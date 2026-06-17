"""RAG chain for question answering."""

import time
import json
import logging
from typing import AsyncGenerator, List, Dict, Any, Optional

from .config import settings
from .vectordb import get_vector_db
from .document import get_embedding_function

logger = logging.getLogger(__name__)


class RAGChain:
    """RAG (Retrieval Augmented Generation) chain."""

    def __init__(self):
        self.vector_db = get_vector_db()

    def retrieve(
        self,
        kb_id: str,
        query: str,
        top_k: int = 5,
        embedding_model: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieve relevant chunks for a query."""
        emb_fn = None
        if embedding_model:
            emb_fn = get_embedding_function(embedding_model)

        results = self.vector_db.search(
            kb_id=kb_id,
            query=query,
            top_k=top_k,
            embedding_function=emb_fn,
        )
        return results

    def _format_context(self, chunks: List[Dict[str, Any]]) -> str:
        """Format retrieved chunks into context string."""
        context_parts = []
        for i, chunk in enumerate(chunks):
            source = chunk.get("metadata", {}).get("source_file", "unknown")
            page = chunk.get("metadata", {}).get("page", "")
            page_info = f" (page {page})" if page else ""
            context_parts.append(
                f"[Source {i + 1}]: {source}{page_info}\n{chunk['content']}\n"
            )

        return "\n---\n".join(context_parts)

    def _build_prompt(self, query: str, context: str) -> str:
        """Build the prompt for the LLM."""
        return f"""你是一个专业的文档问答助手。请根据提供的上下文信息，准确回答用户的问题。

如果上下文中没有足够的信息来回答问题，请如实说明"根据提供的资料，我无法回答这个问题"，不要编造信息。

请用中文回答，保持回答简洁、准确。

上下文信息：
{context}

用户问题：{query}

回答："""

    def _call_llm(self, prompt: str) -> str:
        """Call LLM to generate answer."""
        if settings.llm_provider == "openai":
            return self._call_openai_llm(prompt)
        else:
            return self._call_openai_llm(prompt)  # Default to OpenAI-compatible API

    def _call_openai_llm(self, prompt: str) -> str:
        """Call OpenAI-compatible API."""
        try:
            from openai import OpenAI

            client = OpenAI(
                api_key=settings.llm_api_key or "sk-placeholder",
                base_url=settings.llm_api_base or "https://api.openai.com/v1",
            )

            response = client.chat.completions.create(
                model=settings.llm_model,
                messages=[
                    {"role": "system", "content": "你是一个专业的文档问答助手。"},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=2048,
                stream=False,
            )

            return response.choices[0].message.content or ""
        except Exception as e:
            logger.error("LLM call failed: %s", e)
            return f"（调用大模型时出错：{str(e)}。请检查 API 配置。）"

    def _call_llm_stream(self, prompt: str) -> AsyncGenerator[str, None]:
        """Call LLM with streaming support."""
        return self._call_openai_llm_stream(prompt)

    async def _call_openai_llm_stream(self, prompt: str) -> AsyncGenerator[str, None]:
        """Call OpenAI-compatible API with streaming."""
        try:
            from openai import OpenAI

            client = OpenAI(
                api_key=settings.llm_api_key or "sk-placeholder",
                base_url=settings.llm_api_base or "https://api.openai.com/v1",
            )

            stream = client.chat.completions.create(
                model=settings.llm_model,
                messages=[
                    {"role": "system", "content": "你是一个专业的文档问答助手。"},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=2048,
                stream=True,
            )

            for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            logger.error("LLM stream call failed: %s", e)
            yield f"（调用大模型时出错：{str(e)}。请检查 API 配置。）"

    def qa(
        self,
        kb_id: str,
        query: str,
        top_k: int = 5,
        embedding_model: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Run QA: retrieve + generate."""
        start_time = time.time()

        # Retrieve
        chunks = self.retrieve(kb_id, query, top_k, embedding_model)

        if not chunks:
            elapsed = (time.time() - start_time) * 1000
            return {
                "answer": "知识库中未找到相关文档，无法回答该问题。",
                "sources": [],
                "elapsed_ms": round(elapsed, 2),
            }

        # Generate
        context = self._format_context(chunks)
        prompt = self._build_prompt(query, context)
        answer = self._call_llm(prompt)

        elapsed = (time.time() - start_time) * 1000

        return {
            "answer": answer,
            "sources": chunks,
            "elapsed_ms": round(elapsed, 2),
        }

    async def qa_stream(
        self,
        kb_id: str,
        query: str,
        top_k: int = 5,
        embedding_model: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """Run QA with streaming response."""
        # First yield the sources as JSON
        chunks = self.retrieve(kb_id, query, top_k, embedding_model)

        sources_json = json.dumps(
            [{"id": c["id"], "content": c["content"], "score": c["score"]} for c in chunks],
            ensure_ascii=False,
        )
        yield f"__SOURCES__:{sources_json}\n"

        if not chunks:
            yield "知识库中未找到相关文档，无法回答该问题。"
            return

        context = self._format_context(chunks)
        prompt = self._build_prompt(query, context)

        async for token in self._call_llm_stream(prompt):
            yield token


def get_rag_chain() -> RAGChain:
    """Get RAG chain instance."""
    return RAGChain()
