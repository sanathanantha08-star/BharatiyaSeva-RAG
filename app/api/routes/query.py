from __future__ import annotations
from fastapi import APIRouter
from app.models.retrieval import RetrievalRequest, RetrievedChunk
from app.services.retrieval.hybrid_retriever import HybridRetriever
from app.services.retrieval.parent_fetcher import ParentFetcher
from app.services.retrieval.bm25_retriever import BM25Retriever
from app.services.retrieval.vector_retriever import VectorRetriever
from typing import List

router = APIRouter()

_retriever = HybridRetriever(retrievers=[
    VectorRetriever(),
    BM25Retriever(),
])
_parent_fetcher = ParentFetcher()


@router.post("/", response_model=List[RetrievedChunk])
async def query_documents(request: RetrievalRequest):
    chunks = await _retriever.retrieve(request)
    chunks = await _parent_fetcher.fetch(chunks)
    return chunks