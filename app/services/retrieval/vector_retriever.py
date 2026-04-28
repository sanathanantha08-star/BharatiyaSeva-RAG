from __future__ import annotations
import logging
import numpy as np
from typing import List
from app.core.config import settings
from app.db.mongodb.client import get_db
from app.interfaces.retrieval import IRetriever
from app.models.retrieval import RetrievalRequest, RetrievedChunk
from app.services.ingestion.embedding_service import SentenceTransformerEmbeddingService

logger = logging.getLogger(__name__)


class VectorRetriever(IRetriever):

    def __init__(self, embedder: SentenceTransformerEmbeddingService | None = None):
        self._embedder = embedder or SentenceTransformerEmbeddingService()

    async def retrieve(self, request: RetrievalRequest) -> List[RetrievedChunk]:
        vectors = await self._embedder.embed_batch([request.query])
        query_vector = np.array(vectors[0])

        col = get_db()[settings.mongodb_collection_chunks]
        mongo_filter = {"metadata.chunk_type": "child", "embedding": {"$ne": None}}
        if request.state:
            mongo_filter["metadata.state"] = request.state
        if request.category:
            mongo_filter["metadata.category"] = request.category
        if request.ministry:
            mongo_filter["metadata.ministry"] = request.ministry

        scored = []
        async for doc in col.find(mongo_filter, {"text": 1, "metadata": 1, "embedding": 1}):
            emb = np.array(doc["embedding"])
            score = float(np.dot(query_vector, emb) / (np.linalg.norm(query_vector) * np.linalg.norm(emb) + 1e-10))
            scored.append((score, doc))

        scored.sort(key=lambda x: x[0], reverse=True)

        results = []
        for score, doc in scored[:request.top_k]:
            results.append(RetrievedChunk(
                chunk_id=str(doc["_id"]),
                text=doc["text"],
                score=score,
                retriever="vector",
                metadata=doc.get("metadata", {}),
            ))

        logger.debug("VectorRetriever returned %d chunks", len(results))
        return results