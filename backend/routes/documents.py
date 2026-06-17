"""Document management routes."""

import os
import uuid
import shutil
import logging
import time
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from ..database import (
    get_db,
    get_knowledge_base,
    create_document,
    get_document,
    list_documents,
    update_document,
    delete_document as delete_document_record,
)
from ..models import DocumentResponse
from ..document import process_document, get_embedding_function
from ..vectordb import get_vector_db
from ..config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/documents", tags=["Documents"])

ALLOWED_EXTENSIONS = {".pdf", ".txt", ".md", ".markdown", ".docx", ".doc"}


def _is_allowed(filename: str) -> bool:
    ext = os.path.splitext(filename)[1].lower()
    return ext in ALLOWED_EXTENSIONS


@router.get("", response_model=List[DocumentResponse])
async def list_docs(
    kb_id: Optional[str] = Query(None, description="Filter by knowledge base ID"),
    db: Session = Depends(get_db),
):
    """List all documents, optionally filtered by knowledge base."""
    docs = list_documents(db, kb_id)
    return [doc.to_dict() for doc in docs]


@router.post("/upload", status_code=201)
async def upload_document(
    kb_id: str = Form(...),
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
):
    """Upload document(s) to a knowledge base."""
    # Verify knowledge base exists
    kb = get_knowledge_base(db, kb_id)
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")

    results = []

    for file in files:
        if not _is_allowed(file.filename):
            results.append({
                "filename": file.filename,
                "status": "failed",
                "error": f"不支持的文件类型。支持: {', '.join(ALLOWED_EXTENSIONS)}",
            })
            continue

        # Save file to uploads directory
        file_ext = os.path.splitext(file.filename)[1]
        file_id = str(uuid.uuid4())
        saved_filename = f"{file_id}{file_ext}"
        file_path = os.path.join(settings.upload_dir, saved_filename)

        try:
            content = await file.read()
            with open(file_path, "wb") as f:
                f.write(content)
        except Exception as e:
            logger.error("Failed to save file %s: %s", file.filename, e)
            results.append({
                "filename": file.filename,
                "status": "failed",
                "error": f"文件保存失败: {str(e)}",
            })
            continue

        # Determine file type
        from ..document import get_file_type
        file_type = get_file_type(file.filename)

        # Create document record
        doc_id = str(uuid.uuid4())
        doc_data = {
            "id": doc_id,
            "kb_id": kb_id,
            "filename": file.filename,
            "file_path": file_path,
            "file_type": file_type,
            "file_size": len(content),
            "status": "pending",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }

        doc = create_document(db, doc_data)
        results.append({
            "id": doc_id,
            "filename": file.filename,
            "status": "pending",
            "message": "文件上传成功，等待处理",
        })

    return {"results": results}


@router.post("/{doc_id}/process")
async def process_doc(doc_id: str, db: Session = Depends(get_db)):
    """Process a document: extract text, chunk, and index to vector store."""
    doc = get_document(db, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")

    # Update status
    update_document(db, doc_id, {"status": "processing"})

    try:
        kb = get_knowledge_base(db, doc.kb_id)
        if not kb:
            update_document(db, doc_id, {"status": "failed", "error_message": "知识库不存在"})
            raise HTTPException(status_code=404, detail="知识库不存在")

        # Process document
        texts, metadatas, chunk_ids = process_document(
            file_path=doc.file_path,
            kb_id=doc.kb_id,
            doc_id=doc.id,
            chunk_size=kb.chunk_size,
            chunk_overlap=kb.chunk_overlap,
        )

        # Index to vector database
        vec_db = get_vector_db()
        emb_fn = get_embedding_function(kb.embedding_model)

        vec_db.add_documents(
            kb_id=doc.kb_id,
            chunk_ids=chunk_ids,
            texts=texts,
            metadatas=metadatas,
            embedding_function=emb_fn,
        )

        # Update document record
        update_document(db, doc_id, {
            "status": "indexed",
            "chunk_count": len(chunk_ids),
        })

        return {
            "id": doc_id,
            "status": "indexed",
            "chunk_count": len(chunk_ids),
            "message": f"文档处理完成，生成 {len(chunk_ids)} 个向量块",
        }

    except Exception as e:
        logger.error("Failed to process document %s: %s", doc_id, e, exc_info=True)
        update_document(db, doc_id, {"status": "failed", "error_message": str(e)})
        raise HTTPException(status_code=500, detail=f"文档处理失败: {str(e)}")


@router.post("/batch-process")
async def batch_process_documents(
    kb_id: str = Form(...),
    db: Session = Depends(get_db),
):
    """Process all pending documents in a knowledge base."""
    kb = get_knowledge_base(db, kb_id)
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")

    docs = list_documents(db, kb_id)
    pending_docs = [d for d in docs if d.status == "pending"]

    if not pending_docs:
        return {"message": "没有待处理的文档", "processed": 0}

    results = []
    for doc in pending_docs:
        try:
            # Process
            update_document(db, doc.id, {"status": "processing"})
            texts, metadatas, chunk_ids = process_document(
                file_path=doc.file_path,
                kb_id=kb_id,
                doc_id=doc.id,
                chunk_size=kb.chunk_size,
                chunk_overlap=kb.chunk_overlap,
            )

            vec_db = get_vector_db()
            emb_fn = get_embedding_function(kb.embedding_model)
            vec_db.add_documents(
                kb_id=kb_id,
                chunk_ids=chunk_ids,
                texts=texts,
                metadatas=metadatas,
                embedding_function=emb_fn,
            )

            update_document(db, doc.id, {"status": "indexed", "chunk_count": len(chunk_ids)})
            results.append({
                "id": doc.id,
                "filename": doc.filename,
                "status": "indexed",
                "chunk_count": len(chunk_ids),
            })

        except Exception as e:
            logger.error("Failed to process %s: %s", doc.filename, e)
            update_document(db, doc.id, {"status": "failed", "error_message": str(e)})
            results.append({"id": doc.id, "filename": doc.filename, "status": "failed", "error": str(e)})

    return {"results": results, "processed": len(results)}


@router.get("/{doc_id}", response_model=DocumentResponse)
async def get_doc(doc_id: str, db: Session = Depends(get_db)):
    """Get a document by ID."""
    doc = get_document(db, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    return doc.to_dict()


@router.get("/{doc_id}/chunks")
async def get_doc_chunks(doc_id: str, db: Session = Depends(get_db)):
    """Get chunks for a document."""
    doc = get_document(db, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")

    vec_db = get_vector_db()
    chunks = vec_db.get_chunks_by_document(doc.kb_id, doc.id)

    return {"chunks": chunks, "total": len(chunks)}


@router.get("/{doc_id}/content")
async def get_doc_content(doc_id: str, db: Session = Depends(get_db)):
    """Get the original content of a document."""
    doc = get_document(db, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")

    if not os.path.exists(doc.file_path):
        raise HTTPException(status_code=404, detail="文件不存在")

    try:
        with open(doc.file_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        return {"id": doc.id, "filename": doc.filename, "content": content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取文件失败: {str(e)}")


@router.delete("/{doc_id}")
async def delete_doc(doc_id: str, db: Session = Depends(get_db)):
    """Delete a document and its vector data."""
    doc = get_document(db, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")

    # Delete from vector store
    vec_db = get_vector_db()
    vec_db.delete_document_chunks(doc.kb_id, doc.id)

    # Delete physical file
    if os.path.exists(doc.file_path):
        os.remove(doc.file_path)

    # Delete database record
    delete_document_record(db, doc_id)

    return {"message": f"文档 '{doc.filename}' 已删除"}
