from __future__ import annotations
from fastapi import APIRouter
from pydantic import BaseModel
from app.models.retrieval import RetrievalRequest, QueryResponse, AudioQueryResponse
from app.services.retrieval.hybrid_retriever import HybridRetriever
from app.services.retrieval.parent_fetcher import ParentFetcher
from app.services.retrieval.bm25_retriever import BM25Retriever
from app.services.retrieval.vector_retriever import VectorRetriever
from app.services.llm.llm_service import LLMService
from app.services.llm.tts_service import text_to_audio_base64

router = APIRouter()

_retriever = HybridRetriever(retrievers=[VectorRetriever(), BM25Retriever()])
_parent_fetcher = ParentFetcher()
_llm_service = LLMService()


@router.post("/", response_model=QueryResponse)
async def query_documents(request: RetrievalRequest):
    chunks = await _retriever.retrieve(request)
    chunks = await _parent_fetcher.fetch(chunks)
    answer = await _llm_service.generate(request.query, chunks)
    return QueryResponse(query=request.query, answer=answer, source_chunks=chunks)


@router.post("/voice", response_model=AudioQueryResponse)
async def query_voice(request: RetrievalRequest):
    """Same as /query but also returns audio_base64 of the answer."""
    chunks = await _retriever.retrieve(request)
    chunks = await _parent_fetcher.fetch(chunks)
    answer = await _llm_service.generate(request.query, chunks)
    audio_b64 = await text_to_audio_base64(answer)
    return AudioQueryResponse(
        query=request.query,
        answer=answer,
        audio_base64=audio_b64,
        source_chunks=chunks,
    )