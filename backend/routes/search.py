"""Search and QA routes."""

import json
import time
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ..database import get_db, get_knowledge_base
from ..models import SearchRequest, SearchResult, QARequest, QAResponse
from ..rag_chain import get_rag_chain, RAGChain
from ..vectordb import get_vector_db
from ..document import get_embedding_function

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/search", tags=["Search & QA"])


@router.post("/retrieve", response_model=dict)
async def search_documents(request: SearchRequest, db: Session = Depends(get_db)):
    """Retrieve relevant chunks for a query."""
    kb = get_knowledge_base(db, request.kb_id)
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")

    start_time = time.time()

    vec_db = get_vector_db()
    emb_fn = get_embedding_function(kb.embedding_model)

    chunks = vec_db.search(
        kb_id=request.kb_id,
        query=request.query,
        top_k=request.top_k or kb.top_k,
        embedding_function=emb_fn,
    )

    elapsed = (time.time() - start_time) * 1000

    return {
        "chunks": chunks,
        "total": len(chunks),
        "elapsed_ms": round(elapsed, 2),
    }


@router.post("/qa", response_model=dict)
async def question_answering(request: QARequest, db: Session = Depends(get_db)):
    """Run RAG question answering."""
    kb = get_knowledge_base(db, request.kb_id)
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")

    rag = get_rag_chain()
    result = rag.qa(
        kb_id=request.kb_id,
        query=request.query,
        top_k=request.top_k or kb.top_k,
        embedding_model=kb.embedding_model,
    )

    return result


@router.post("/qa/stream")
async def question_answering_stream(request: QARequest, db: Session = Depends(get_db)):
    """Run RAG question answering with streaming output."""
    kb = get_knowledge_base(db, request.kb_id)
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")

    rag = get_rag_chain()

    async def generate():
        async for token in rag.qa_stream(
            kb_id=request.kb_id,
            query=request.query,
            top_k=request.top_k or kb.top_k,
            embedding_model=kb.embedding_model,
        ):
            yield token

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
