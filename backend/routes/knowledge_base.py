"""Knowledge base management routes."""

import uuid
import logging
from datetime import datetime
from typing import List

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from ..database import (
    get_db,
    create_knowledge_base,
    get_knowledge_base,
    get_knowledge_base_by_name,
    list_knowledge_bases,
    update_knowledge_base,
    delete_knowledge_base,
)
from ..models import KnowledgeBaseCreate, KnowledgeBaseUpdate, KnowledgeBaseResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/knowledge-bases", tags=["Knowledge Bases"])


@router.get("", response_model=List[KnowledgeBaseResponse])
async def list_kbs(db: Session = Depends(get_db)):
    """List all knowledge bases."""
    kbs = list_knowledge_bases(db)
    return [kb.to_dict() for kb in kbs]


@router.post("", response_model=KnowledgeBaseResponse, status_code=201)
async def create_kb(data: KnowledgeBaseCreate, db: Session = Depends(get_db)):
    """Create a new knowledge base."""
    # Check name uniqueness
    existing = get_knowledge_base_by_name(db, data.name)
    if existing:
        raise HTTPException(status_code=400, detail=f"知识库名称 '{data.name}' 已存在")

    kb_data = {
        "id": str(uuid.uuid4()),
        "name": data.name,
        "description": data.description,
        "embedding_model": data.embedding_model,
        "chunk_size": data.chunk_size,
        "chunk_overlap": data.chunk_overlap,
        "top_k": data.top_k,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }

    kb = create_knowledge_base(db, kb_data)
    return kb.to_dict()


@router.get("/{kb_id}", response_model=KnowledgeBaseResponse)
async def get_kb(kb_id: str, db: Session = Depends(get_db)):
    """Get a knowledge base by ID."""
    kb = get_knowledge_base(db, kb_id)
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")
    return kb.to_dict()


@router.put("/{kb_id}", response_model=KnowledgeBaseResponse)
async def update_kb(kb_id: str, data: KnowledgeBaseUpdate, db: Session = Depends(get_db)):
    """Update a knowledge base."""
    kb = get_knowledge_base(db, kb_id)
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")

    update_data = data.model_dump(exclude_none=True)

    # Check name uniqueness if changing name
    if "name" in update_data:
        existing = get_knowledge_base_by_name(db, update_data["name"])
        if existing and existing.id != kb_id:
            raise HTTPException(status_code=400, detail=f"知识库名称 '{update_data['name']}' 已存在")

    kb = update_knowledge_base(db, kb_id, update_data)
    return kb.to_dict()


@router.delete("/{kb_id}")
async def delete_kb(kb_id: str, db: Session = Depends(get_db)):
    """Delete a knowledge base."""
    kb = get_knowledge_base(db, kb_id)
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")

    success = delete_knowledge_base(db, kb_id)
    if not success:
        raise HTTPException(status_code=500, detail="删除知识库失败")

    return {"message": f"知识库 '{kb.name}' 已删除"}
