"""
app/interfaces/ingestion.py
───────────────────────────
Abstract interfaces for the ingestion pipeline components.
Concrete implementations live in app/services/ingestion/.
Coding against interfaces keeps the system testable and swappable.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Tuple

from app.models.document import ChunkRecord, DocumentRecord


# ─────────────────────────────────────────────────────────────────────────────

class IPDFParser(ABC):
    """Parses a raw PDF into per-page (text, page_number) tuples."""

    @abstractmethod
    async def parse(self, pdf_path: Path) -> List[Tuple[str, int]]:
        """
        Returns a list of (page_text, page_number) for every page
        that yields extractable text.
        """


class ITextCleaner(ABC):
    """Cleans raw text extracted from a PDF page."""

    @abstractmethod
    def clean(self, raw_text: str) -> str:
        """Return cleaned, normalised text."""


class IChunkingStrategy(ABC):
    """Splits cleaned page texts into parent + child chunks."""

    @abstractmethod
    def chunk(
        self,
        pages: List[Tuple[str, int]],
        doc_record: DocumentRecord,
    ) -> Tuple[List[ChunkRecord], List[ChunkRecord]]:
        """
        Returns (parent_chunks, child_chunks).
        Each child chunk carries a reference to its parent_chunk_id.
        """


class IEmbeddingService(ABC):
    """Generates dense embedding vectors for text."""

    @abstractmethod
    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Returns a list of embedding vectors, one per input text."""


class IDocumentRepository(ABC):
    """Persistence interface for DocumentRecord objects."""

    @abstractmethod
    async def upsert(self, record: DocumentRecord) -> None: ...

    @abstractmethod
    async def get_by_id(self, doc_id: str) -> DocumentRecord | None: ...

    @abstractmethod
    async def update_status(self, doc_id: str, status, error: str = "") -> None: ...


class IChunkRepository(ABC):
    """Persistence interface for ChunkRecord objects (text store)."""

    @abstractmethod
    async def upsert_batch(self, chunks: List[ChunkRecord]) -> None: ...


class IVectorRepository(ABC):
    """Persistence interface for chunk vectors (vector store)."""

    @abstractmethod
    async def upsert_vectors(self, chunks: List[ChunkRecord]) -> None:
        """
        Upserts chunk_id + embedding + metadata into the vector store.
        Only child chunks with non-None embeddings should be passed.
        """
