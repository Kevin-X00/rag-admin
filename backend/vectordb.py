"""Vector database operations with ChromaDB."""

import os
import logging
from typing import List, Dict, Any, Optional
from functools import lru_cache

import chromadb
from chromadb.config import Settings as ChromaSettings

from .config import settings

logger = logging.getLogger(__name__)


class VectorDBManager:
    """Manages ChromaDB collections for knowledge bases."""

    def __init__(self):
        self.persist_dir = settings.chroma_persist_dir
        os.makedirs(self.persist_dir, exist_ok=True)

        self.client = chromadb.PersistentClient(
            path=self.persist_dir,
            settings=ChromaSettings(
                anonymized_telemetry=False,
                allow_reset=True,
            ),
        )

    def get_or_create_collection(self, kb_id: str, embedding_function=None):
        """Get or create a collection for a knowledge base."""
        return self.client.get_or_create_collection(
            name=kb_id,
            embedding_function=embedding_function,
            metadata={"kb_id": kb_id},
        )

    def get_collection(self, kb_id: str):
        """Get an existing collection."""
        try:
            return self.client.get_collection(name=kb_id)
        except ValueError:
            return None

    def delete_collection(self, kb_id: str):
        """Delete a collection."""
        try:
            self.client.delete_collection(name=kb_id)
            return True
        except ValueError:
            return False

    def add_documents(
        self,
        kb_id: str,
        chunk_ids: List[str],
        texts: List[str],
        metadatas: List[Dict[str, Any]],
        embedding_function=None,
    ):
        """Add document chunks to vector store."""
        collection = self.get_or_create_collection(kb_id, embedding_function)
        collection.add(
            ids=chunk_ids,
            documents=texts,
            metadatas=metadatas,
        )
        return len(chunk_ids)

    def search(
        self,
        kb_id: str,
        query: str,
        top_k: int = 5,
        embedding_function=None,
    ) -> List[Dict[str, Any]]:
        """Search for similar chunks."""
        collection = self.get_collection(kb_id)
        if collection is None:
            return []

        results = collection.query(
            query_texts=[query],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )

        chunks = []
        if results["ids"] and results["ids"][0]:
            for i, doc_id in enumerate(results["ids"][0]):
                # Chroma returns distances; convert to similarity score (1 - distance)
                distance = results["distances"][0][i] if results["distances"] else 0
                score = max(0.0, 1.0 - distance)

                chunks.append({
                    "id": doc_id,
                    "content": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                    "score": round(score, 4),
                })

        return chunks

    def get_chunks_by_document(self, kb_id: str, doc_id: str) -> List[Dict[str, Any]]:
        """Get all chunks belonging to a specific document."""
        collection = self.get_collection(kb_id)
        if collection is None:
            return []

        results = collection.get(
            where={"doc_id": doc_id},
            include=["documents", "metadatas"],
        )

        chunks = []
        if results["ids"]:
            for i, cid in enumerate(results["ids"]):
                chunks.append({
                    "id": cid,
                    "content": results["documents"][i],
                    "metadata": results["metadatas"][i] if results["metadatas"] else {},
                })

        return chunks

    def delete_document_chunks(self, kb_id: str, doc_id: str):
        """Delete all chunks for a document."""
        collection = self.get_collection(kb_id)
        if collection is None:
            return

        collection.delete(where={"doc_id": doc_id})

    def count_chunks(self, kb_id: str) -> int:
        """Count total chunks in a knowledge base."""
        collection = self.get_collection(kb_id)
        if collection is None:
            return 0
        return collection.count()

    def list_collections(self) -> List[str]:
        """List all collection names."""
        collections = self.client.list_collections()
        return [c.name for c in collections]


@lru_cache()
def get_vector_db() -> VectorDBManager:
    """Get singleton vector database manager."""
    return VectorDBManager()
