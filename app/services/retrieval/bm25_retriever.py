from __future__ import annotations
import logging
import re
from typing import List
from app.db.mongodb.client import get_db
from app.core.config import settings
from app.interfaces.retrieval import IRetriever
from app.models.retrieval import RetrievalRequest, RetrievedChunk

logger = logging.getLogger(__name__)


class BM25Retriever(IRetriever):

    async def retrieve(self, request: RetrievalRequest) -> List[RetrievedChunk]:
        col = get_db()[settings.mongodb_collection_chunks]
        terms = re.split(r"\s+", request.query.strip())
        regex = "|".join(re.escape(t) for t in terms)

        mongo_filter = {
            "text": {"$regex": regex, "$options": "i"},
            "metadata.chunk_type": "child",
        }
        if request.state:
            mongo_filter["metadata.state"] = request.state
        if request.category:
            mongo_filter["metadata.category"] = request.category
        if request.ministry:
            mongo_filter["metadata.ministry"] = request.ministry

        results = []
        async for doc in col.find(mongo_filter, {"text": 1, "metadata": 1}).limit(request.top_k):
            results.append(RetrievedChunk(
                chunk_id=str(doc["_id"]),
                text=doc["text"],
                score=1.0,
                retriever="bm25",
                metadata=doc.get("metadata", {}),
            ))

        logger.debug("BM25Retriever returned %d chunks", len(results))
        return results