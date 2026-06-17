"""Pydantic data models for RAG Admin."""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


# ---- Knowledge Base ----

class KnowledgeBaseCreate(BaseModel):
    name: str = Field(..., description="Knowledge base name")
    description: str = Field("", description="Knowledge base description")
    embedding_model: str = Field("BAAI/bge-small-zh-v1.5", description="Embedding model name")
    chunk_size: int = Field(512, description="Chunk size for document splitting")
    chunk_overlap: int = Field(64, description="Chunk overlap")
    top_k: int = Field(5, description="Default top-k for retrieval")


class KnowledgeBaseUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    embedding_model: Optional[str] = None
    chunk_size: Optional[int] = None
    chunk_overlap: Optional[int] = None
    top_k: Optional[int] = None


class KnowledgeBaseResponse(BaseModel):
    id: str
    name: str
    description: str
    embedding_model: str
    chunk_size: int
    chunk_overlap: int
    top_k: int
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


# ---- Document ----

class DocumentResponse(BaseModel):
    id: str
    kb_id: str
    filename: str
    file_type: str
    file_size: int
    status: str
    chunk_count: int
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class DocumentChunk(BaseModel):
    id: str
    content: str
    metadata: Dict[str, Any]
    score: Optional[float] = None


# ---- Search / QA ----

class SearchRequest(BaseModel):
    kb_id: str = Field(..., description="Knowledge base ID")
    query: str = Field(..., description="Search query")
    top_k: int = Field(5, description="Number of results to return")


class SearchResult(BaseModel):
    chunks: List[DocumentChunk]
    elapsed_ms: float


class QARequest(BaseModel):
    kb_id: str = Field(..., description="Knowledge base ID")
    query: str = Field(..., description="Question")
    top_k: int = Field(5, description="Number of context chunks")
    stream: bool = Field(False, description="Enable streaming response")


class QAResponse(BaseModel):
    answer: str
    sources: List[DocumentChunk]
    elapsed_ms: float


# ---- Statistics ----

class StatsResponse(BaseModel):
    total_documents: int = 0
    indexed_documents: int = 0
    pending_documents: int = 0
    total_chunks: int = 0
    total_size_bytes: int = 0
