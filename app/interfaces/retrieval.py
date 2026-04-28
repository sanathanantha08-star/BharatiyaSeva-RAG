from __future__ import annotations
from abc import ABC, abstractmethod
from typing import List
from app.models.retrieval import RetrievedChunk, RetrievalRequest


class IRetriever(ABC):
    @abstractmethod
    async def retrieve(self, request: RetrievalRequest) -> List[RetrievedChunk]: ...


class IReranker(ABC):
    @abstractmethod
    async def rerank(self, query: str, chunks: List[RetrievedChunk]) -> List[RetrievedChunk]: ...


class IHybridRetriever(ABC):
    @abstractmethod
    async def retrieve(self, request: RetrievalRequest) -> List[RetrievedChunk]: ...