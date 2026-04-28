from __future__ import annotations
from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class RetrievalRequest(BaseModel):
    query: str
    top_k: int = 5
    # metadata filters – all optional
    state: Optional[str] = None
    category: Optional[str] = None
    ministry: Optional[str] = None
    target_income_max: Optional[float] = None
    target_age: Optional[int] = None


class RetrievedChunk(BaseModel):
    chunk_id: str
    text: str
    score: float
    retriever: str                        # "vector", "bm25", "hybrid"
    metadata: Dict[str, Any] = {}
    parent_text: Optional[str] = None    # populated after parent fetch