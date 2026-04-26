"""
app/services/ingestion/embedding_service.py
─────────────────────────────────────────────
LangChain-backed embedding service using HuggingFaceEmbeddings.

Why LangChain here?
  • HuggingFaceEmbeddings implements LangChain's Embeddings base class,
    making it trivially swappable (OpenAI, Cohere, etc.) later.
  • Identical free model: sentence-transformers/all-MiniLM-L6-v2
  • 384-dim, ~80 MB, runs on CPU, no API key needed.

Swap the model by changing EMBEDDING_MODEL_NAME in .env — zero code change.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import List

from langchain_huggingface import HuggingFaceEmbeddings

from app.core.config import settings
from app.interfaces.ingestion import IEmbeddingService
from app.models.document import ChunkRecord

logger = logging.getLogger(__name__)

_embeddings_instance: HuggingFaceEmbeddings | None = None


def _get_embeddings() -> HuggingFaceEmbeddings:
    """Lazy singleton — model loads from disk only once."""
    global _embeddings_instance
    if _embeddings_instance is None:
        logger.info(
            "Loading LangChain HuggingFaceEmbeddings: %s (device=%s)",
            settings.embedding_model_name,
            settings.embedding_device,
        )
        _embeddings_instance = HuggingFaceEmbeddings(
            model_name=settings.embedding_model_name,
            model_kwargs={"device": settings.embedding_device},
            encode_kwargs={"normalize_embeddings": True},  # unit vectors → cosine sim
        )
        logger.info("Embedding model ready.")
    return _embeddings_instance


class SentenceTransformerEmbeddingService(IEmbeddingService):
    """
    Implements IEmbeddingService using LangChain's HuggingFaceEmbeddings.
    The class name is kept the same so pipeline.py needs zero changes.
    """

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Runs LangChain's embed_documents in a thread-pool (non-blocking)."""
        if not texts:
            return []
        loop = asyncio.get_event_loop()
        vectors = await loop.run_in_executor(
            None,
            _get_embeddings().embed_documents,  # LangChain's batch method
            texts,
        )
        return vectors

    async def embed_chunks(self, chunks: List[ChunkRecord]) -> List[ChunkRecord]:
        """
        Embeds a list of ChunkRecords in-place.
        Stamps embedding_model, embedding_dim, and embedded_at on metadata.
        """
        texts = [c.text for c in chunks]
        vectors = await self.embed_batch(texts)

        for chunk, vector in zip(chunks, vectors):
            chunk.embedding = vector
            chunk.metadata.embedding_model = settings.embedding_model_name
            chunk.metadata.embedding_dim = len(vector)
            chunk.metadata.embedded_at = datetime.utcnow()

        return chunks