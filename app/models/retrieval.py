from __future__ import annotations
from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class RetrievalRequest(BaseModel):
    query: str
    top_k: int = 5
    state: Optional[str] = None
    category: Optional[str] = None
    ministry: Optional[str] = None
    target_income_max: Optional[float] = None
    target_age: Optional[int] = None


class RetrievedChunk(BaseModel):
    chunk_id: str
    text: str
    score: float
    retriever: str
    metadata: Dict[str, Any] = {}
    parent_text: Optional[str] = None


class QueryResponse(BaseModel):
    query: str
    answer: str
    source_chunks: List[RetrievedChunk]


class AudioQueryResponse(BaseModel):
    query: str          # transcribed text
    answer: str         # LLM text answer
    audio_base64: str   # mp3 base64 encoded
    source_chunks: List[RetrievedChunk]