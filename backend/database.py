"""SQLite database operations for RAG Admin."""

import os
import shutil
import json
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import create_engine, Column, String, Text, Integer, Float, DateTime, JSON, ForeignKey
from sqlalchemy.orm import sessionmaker, declarative_base, relationship, Session
from contextlib import contextmanager

from .config import settings

Base = declarative_base()


# ---- SQLAlchemy Models ----

class KnowledgeBase(Base):
    __tablename__ = "knowledge_bases"

    id = Column(String(36), primary_key=True)
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text, default="")
    embedding_model = Column(String(255), default=settings.embedding_model)
    chunk_size = Column(Integer, default=settings.default_chunk_size)
    chunk_overlap = Column(Integer, default=settings.default_chunk_overlap)
    top_k = Column(Integer, default=settings.default_top_k)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    documents = relationship("Document", back_populates="knowledge_base", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "embedding_model": self.embedding_model,
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap,
            "top_k": self.top_k,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class Document(Base):
    __tablename__ = "documents"

    id = Column(String(36), primary_key=True)
    kb_id = Column(String(36), ForeignKey("knowledge_bases.id", ondelete="CASCADE"), nullable=False)
    filename = Column(String(255), nullable=False)
    file_path = Column(Text, nullable=False)
    file_type = Column(String(50), nullable=False)  # pdf, txt, md, docx
    file_size = Column(Integer, default=0)
    status = Column(String(50), default="pending")  # pending, processing, indexed, failed
    chunk_count = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    knowledge_base = relationship("KnowledgeBase", back_populates="documents")

    def to_dict(self):
        return {
            "id": self.id,
            "kb_id": self.kb_id,
            "filename": self.filename,
            "file_path": self.file_path,
            "file_type": self.file_type,
            "file_size": self.file_size,
            "status": self.status,
            "chunk_count": self.chunk_count,
            "error_message": self.error_message,
            "metadata": self.metadata_json,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


# ---- Database Engine ----

_db_engine = None
_db_session_local = None


def get_engine():
    global _db_engine
    if _db_engine is None:
        db_path = settings.database_url.replace("sqlite:///", "")
        if not os.path.isabs(db_path):
            db_path = os.path.join(settings.data_dir, os.path.basename(db_path))
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        _db_engine = create_engine(f"sqlite:///{db_path}", echo=False, connect_args={"check_same_thread": False})
    return _db_engine


def get_session_local():
    global _db_session_local
    if _db_session_local is None:
        engine = get_engine()
        _db_session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return _db_session_local


def init_db():
    """Initialize database and create tables."""
    engine = get_engine()
    Base.metadata.create_all(bind=engine)


@contextmanager
def get_db() -> Session:
    """Context manager for database sessions."""
    session_local = get_session_local()
    db = session_local()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# ---- CRUD Operations ----

def create_knowledge_base(db: Session, kb_data: dict) -> KnowledgeBase:
    """Create a new knowledge base."""
    kb = KnowledgeBase(**kb_data)
    db.add(kb)
    db.commit()
    db.refresh(kb)
    return kb


def get_knowledge_base(db: Session, kb_id: str) -> Optional[KnowledgeBase]:
    """Get knowledge base by ID."""
    return db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()


def get_knowledge_base_by_name(db: Session, name: str) -> Optional[KnowledgeBase]:
    """Get knowledge base by name."""
    return db.query(KnowledgeBase).filter(KnowledgeBase.name == name).first()


def list_knowledge_bases(db: Session) -> List[KnowledgeBase]:
    """List all knowledge bases."""
    return db.query(KnowledgeBase).order_by(KnowledgeBase.created_at.desc()).all()


def update_knowledge_base(db: Session, kb_id: str, kb_data: dict) -> Optional[KnowledgeBase]:
    """Update a knowledge base."""
    kb = get_knowledge_base(db, kb_id)
    if kb:
        for key, value in kb_data.items():
            if hasattr(kb, key):
                setattr(kb, key, value)
        kb.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(kb)
    return kb


def delete_knowledge_base(db: Session, kb_id: str) -> bool:
    """Delete a knowledge base and its vector data."""
    kb = get_knowledge_base(db, kb_id)
    if kb:
        # Delete vector data directory
        chroma_kb_dir = os.path.join(settings.chroma_persist_dir, kb_id)
        if os.path.exists(chroma_kb_dir):
            shutil.rmtree(chroma_kb_dir, ignore_errors=True)
        db.delete(kb)
        db.commit()
        return True
    return False


def create_document(db: Session, doc_data: dict) -> Document:
    """Create a document record."""
    doc = Document(**doc_data)
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


def get_document(db: Session, doc_id: str) -> Optional[Document]:
    """Get document by ID."""
    return db.query(Document).filter(Document.id == doc_id).first()


def list_documents(db: Session, kb_id: Optional[str] = None) -> List[Document]:
    """List documents, optionally filtered by knowledge base."""
    query = db.query(Document)
    if kb_id:
        query = query.filter(Document.kb_id == kb_id)
    return query.order_by(Document.created_at.desc()).all()


def update_document(db: Session, doc_id: str, doc_data: dict) -> Optional[Document]:
    """Update a document record."""
    doc = get_document(db, doc_id)
    if doc:
        for key, value in doc_data.items():
            if hasattr(doc, key):
                setattr(doc, key, value)
        doc.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(doc)
    return doc


def delete_document(db: Session, doc_id: str) -> bool:
    """Delete a document record (file deletion handled elsewhere)."""
    doc = get_document(db, doc_id)
    if doc:
        db.delete(doc)
        db.commit()
        return True
    return False


def get_kb_stats(db: Session, kb_id: str) -> Dict[str, Any]:
    """Get statistics for a knowledge base."""
    kb = get_knowledge_base(db, kb_id)
    if not kb:
        return {}

    docs = db.query(Document).filter(Document.kb_id == kb_id).all()
    total_docs = len(docs)
    indexed_docs = sum(1 for d in docs if d.status == "indexed")
    total_chunks = sum(d.chunk_count or 0 for d in docs)
    total_size = sum(d.file_size or 0 for d in docs)

    return {
        "total_documents": total_docs,
        "indexed_documents": indexed_docs,
        "pending_documents": total_docs - indexed_docs,
        "total_chunks": total_chunks,
        "total_size_bytes": total_size,
    }
