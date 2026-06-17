"""Statistics routes."""

import logging
from typing import List, Dict, Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db, list_knowledge_bases, get_kb_stats, get_document
from ..vectordb import get_vector_db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/stats", tags=["Statistics"])


@router.get("/overview")
async def get_overview(db: Session = Depends(get_db)):
    """Get overview statistics for all knowledge bases."""
    kbs = list_knowledge_bases(db)
    vec_db = get_vector_db()

    total_docs = 0
    total_indexed = 0
    total_chunks = 0
    kb_stats_list = []

    for kb in kbs:
        stats = get_kb_stats(db, kb.id)
        kb_chunks = vec_db.count_chunks(kb.id)

        total_docs += stats["total_documents"]
        total_indexed += stats["indexed_documents"]
        total_chunks += kb_chunks

        kb_stats_list.append({
            "id": kb.id,
            "name": kb.name,
            "documents": stats["total_documents"],
            "indexed": stats["indexed_documents"],
            "chunks": kb_chunks,
        })

    return {
        "total_knowledge_bases": len(kbs),
        "total_documents": total_docs,
        "total_indexed_documents": total_indexed,
        "total_chunks": total_chunks,
        "knowledge_bases": kb_stats_list,
    }


@router.get("/kb/{kb_id}")
async def get_kb_stats_endpoint(kb_id: str, db: Session = Depends(get_db)):
    """Get statistics for a specific knowledge base."""
    stats = get_kb_stats(db, kb_id)
    if not stats:
        return {"error": "知识库不存在"}

    vec_db = get_vector_db()
    stats["vector_chunks"] = vec_db.count_chunks(kb_id)
    return stats
