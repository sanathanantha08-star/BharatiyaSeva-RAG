from __future__ import annotations
import asyncio
import logging
from typing import Dict, List
from app.interfaces.retrieval import IHybridRetriever, IRetriever
from app.models.retrieval import RetrievalRequest, RetrievedChunk
from app.services.retrieval.vector_retriever import VectorRetriever
from app.services.retrieval.bm25_retriever import BM25Retriever

logger = logging.getLogger(__name__)

RRF_K = 60   # standard RRF constant


class HybridRetriever(IHybridRetriever):
    """
    Runs all injected retrievers in parallel via asyncio.gather,
    then merges results using Reciprocal Rank Fusion (RRF).

    SOLID – Open/Closed:
    Add a new retriever by passing it in retrievers list. No code change here.
    """

    def __init__(self, retrievers: List[IRetriever] | None = None):
        self._retrievers = retrievers or [
            VectorRetriever(),
            BM25Retriever(),
        ]

    async def retrieve(self, request: RetrievalRequest) -> List[RetrievedChunk]:
        # Run all retrievers in parallel
        results_per_retriever = await asyncio.gather(
            *[r.retrieve(request) for r in self._retrievers],
            return_exceptions=False,
        )

        fused = self._rrf(results_per_retriever, top_k=request.top_k)
        logger.debug("HybridRetriever returning %d fused chunks", len(fused))
        return fused

    def _rrf(
        self,
        results_per_retriever: List[List[RetrievedChunk]],
        top_k: int,
    ) -> List[RetrievedChunk]:
        scores: Dict[str, float] = {}
        chunks: Dict[str, RetrievedChunk] = {}

        for results in results_per_retriever:
            for rank, chunk in enumerate(results):
                rrf_score = 1.0 / (RRF_K + rank + 1)
                scores[chunk.chunk_id] = scores.get(chunk.chunk_id, 0.0) + rrf_score
                if chunk.chunk_id not in chunks:
                    chunks[chunk.chunk_id] = chunk

        ranked = sorted(scores.keys(), key=lambda cid: scores[cid], reverse=True)

        fused = []
        for cid in ranked[:top_k]:
            c = chunks[cid]
            c.score = scores[cid]
            c.retriever = "hybrid"
            fused.append(c)

        return fused