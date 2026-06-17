"""Document parsing and processing pipeline."""

import os
import uuid
import hashlib
import logging
from typing import List, Tuple, Optional, Dict, Any
from datetime import datetime

from .config import settings

logger = logging.getLogger(__name__)


def get_file_type(filename: str) -> str:
    """Determine file type from extension."""
    ext = os.path.splitext(filename)[1].lower()
    mapping = {
        ".pdf": "pdf",
        ".txt": "txt",
        ".md": "md",
        ".markdown": "md",
        ".docx": "docx",
        ".doc": "docx",
    }
    return mapping.get(ext, "txt")


def extract_text(file_path: str, file_type: str) -> Tuple[str, Dict[str, Any]]:
    """Extract text from a document file.

    Returns (text_content, metadata).
    """
    metadata = {"source_file": os.path.basename(file_path), "file_type": file_type}

    if file_type == "txt":
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            text = f.read()
        metadata["pages"] = 1

    elif file_type == "md":
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            text = f.read()
        metadata["pages"] = 1

    elif file_type == "pdf":
        text = _extract_pdf_text(file_path)
        metadata["pages"] = text.count("\f") + 1 if text else 0

    elif file_type == "docx":
        text = _extract_docx_text(file_path)
        metadata["pages"] = 1

    else:
        raise ValueError(f"Unsupported file type: {file_type}")

    return text, metadata


def _extract_pdf_text(file_path: str) -> str:
    """Extract text from PDF using PyMuPDF."""
    try:
        import fitz  # PyMuPDF
    except ImportError:
        logger.warning("PyMuPDF not installed, trying pdfminer...")
        try:
            from pdfminer.high_level import extract_text as pdfminer_extract
            return pdfminer_extract(file_path)
        except ImportError:
            raise ImportError(
                "Need PyMuPDF or pdfminer.six to parse PDF files. "
                "Install with: pip install pymupdf pdfminer.six"
            )

    doc = fitz.open(file_path)
    text_parts = []
    for page in doc:
        text_parts.append(page.get_text())
    doc.close()
    return "\n".join(text_parts)


def _extract_docx_text(file_path: str) -> str:
    """Extract text from DOCX using python-docx."""
    try:
        from docx import Document
    except ImportError:
        raise ImportError(
            "Need python-docx to parse DOCX files. "
            "Install with: pip install python-docx"
        )

    doc = Document(file_path)
    text_parts = []
    for para in doc.paragraphs:
        text_parts.append(para.text)
    return "\n".join(text_parts)


def chunk_text(
    text: str,
    chunk_size: int = 512,
    chunk_overlap: int = 64,
) -> List[str]:
    """Split text into overlapping chunks.

    Uses a recursive character splitter that respects paragraph and sentence boundaries.
    """
    if not text.strip():
        return []

    chunks = []
    separators = ["\n\n", "\n", "。", ".", "！", "!", "？", "?", "；", ";", "，", ",", " ", ""]

    def _split(text: str, seps: List[str], chunk_size: int, chunk_overlap: int) -> List[str]:
        if len(text) <= chunk_size:
            if text.strip():
                return [text.strip()]
            return []

        sep = seps[0] if seps else ""

        if sep == "":
            # Character-level split
            result = []
            start = 0
            while start < len(text):
                end = min(start + chunk_size, len(text))
                chunk = text[start:end].strip()
                if chunk:
                    result.append(chunk)
                start += chunk_size - chunk_overlap
            return result

        # Try to split by separator
        parts = text.split(sep)
        result = []
        current_chunk = ""

        for part in parts:
            if not part.strip():
                continue

            separator = sep if current_chunk else ""

            if len(current_chunk) + len(separator) + len(part) <= chunk_size:
                current_chunk += separator + part
            else:
                if current_chunk.strip():
                    result.append(current_chunk.strip())
                current_chunk = part

        if current_chunk.strip():
            result.append(current_chunk.strip())

        # If any chunk is still too large, recursively split with next separator
        final_result = []
        for chunk in result:
            if len(chunk) > chunk_size and len(seps) > 1:
                final_result.extend(_split(chunk, seps[1:], chunk_size, chunk_overlap))
            else:
                final_result.append(chunk)

        return final_result

    chunks = _split(text, separators, chunk_size, chunk_overlap)
    return chunks


def process_document(
    file_path: str,
    kb_id: str,
    doc_id: str,
    chunk_size: int = 512,
    chunk_overlap: int = 64,
) -> Tuple[List[str], List[Dict[str, Any]], List[str]]:
    """Process a document: extract text, split into chunks, prepare for vectorization.

    Returns (texts, metadatas, chunk_ids).
    """
    file_type = get_file_type(os.path.basename(file_path))
    text, doc_metadata = extract_text(file_path, file_type)

    chunks = chunk_text(text, chunk_size, chunk_overlap)

    texts = []
    metadatas = []
    chunk_ids = []

    for i, chunk in enumerate(chunks):
        chunk_id = hashlib.md5(f"{doc_id}_{i}_{chunk[:50]}".encode()).hexdigest()
        chunk_ids.append(chunk_id)
        texts.append(chunk)
        metadatas.append({
            "doc_id": doc_id,
            "kb_id": kb_id,
            "chunk_index": i,
            "source_file": os.path.basename(file_path),
            "file_type": file_type,
            **doc_metadata,
        })

    # Add page number metadata if available
    current_page = 1
    if file_type == "pdf":
        for i, text in enumerate(texts):
            # Rough page estimation
            metadatas[i]["page"] = current_page

    logger.info(
        "Processed document %s: %d chars -> %d chunks",
        os.path.basename(file_path),
        len(text),
        len(chunks),
    )

    return texts, metadatas, chunk_ids


def get_embedding_function(model_name: str):
    """Get embedding function based on model name."""
    from .config import settings as app_settings

    if app_settings.embedding_provider == "openai":
        return _get_openai_embedding_function()
    else:
        return _get_local_embedding_function(model_name)


def _get_local_embedding_function(model_name: str):
    """Get local embedding function using sentence-transformers."""
    try:
        from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

        return SentenceTransformerEmbeddingFunction(model_name=model_name)
    except Exception as e:
        logger.warning(
            "Failed to load local model %s: %s. Falling back to default.",
            model_name,
            e,
        )
        from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

        return SentenceTransformerEmbeddingFunction()


def _get_openai_embedding_function():
    """Get OpenAI embedding function."""
    from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction

    return OpenAIEmbeddingFunction(
        api_key=settings.openai_api_key or "",
        api_base=settings.openai_api_base,
        model_name=settings.openai_embedding_model,
    )
