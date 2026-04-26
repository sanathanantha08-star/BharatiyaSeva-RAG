"""
app/models/document.py
──────────────────────
Pydantic domain models for documents and chunks stored in MongoDB.
These are the canonical data shapes for the entire backend.
"""

from __future__ import annotations

import hashlib
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


# ─────────────────────────────────────────────────────────────────────────────
# Enums
# ─────────────────────────────────────────────────────────────────────────────

class DocumentStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ChunkType(str, Enum):
    PARENT = "parent"
    CHILD = "child"


class ContentType(str, Enum):
    TEXT = "text"
    TABLE = "table"
    IMAGE_CAPTION = "image_caption"


# ─────────────────────────────────────────────────────────────────────────────
# Document Model
# ─────────────────────────────────────────────────────────────────────────────

class DocumentMetadata(BaseModel):
    """Scheme-specific and file-level metadata attached to a document."""

    # File-level
    filename: str
    file_size_bytes: int
    total_pages: int
    file_hash: str  # SHA-256 of raw PDF bytes – used for dedup (future)

    # Scheme-level (parsed from PDF or provided by uploader)
    scheme_name: Optional[str] = None
    ministry: Optional[str] = None
    state: Optional[str] = None          # e.g. "Maharashtra", "All India"
    target_income_max: Optional[float] = None   # in INR per annum
    target_age_min: Optional[int] = None
    target_age_max: Optional[int] = None
    category: Optional[str] = None       # e.g. "Agriculture", "Education"
    language: str = "en"

    # Audit
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)
    source_url: Optional[str] = None


class DocumentRecord(BaseModel):
    """
    Top-level document record stored in MongoDB `documents` collection.
    One record per uploaded PDF.
    """

    doc_id: str                          # UUID generated at upload time
    status: DocumentStatus = DocumentStatus.PENDING
    metadata: DocumentMetadata
    chunk_ids: List[str] = Field(default_factory=list)  # child chunk IDs
    error_message: Optional[str] = None
    processing_started_at: Optional[datetime] = None
    processing_completed_at: Optional[datetime] = None

    def to_mongo(self) -> Dict[str, Any]:
        d = self.model_dump()
        d["_id"] = self.doc_id
        return d


# ─────────────────────────────────────────────────────────────────────────────
# Chunk Models
# ─────────────────────────────────────────────────────────────────────────────

class ChunkMetadata(BaseModel):
    """
    Rich metadata attached to every chunk – used for metadata filtering
    at retrieval time and to support future hybrid retrieval strategies.
    """

    doc_id: str
    chunk_id: str
    chunk_type: ChunkType
    parent_chunk_id: Optional[str] = None  # set on child chunks
    content_type: ContentType = ContentType.TEXT

    # Positional
    page_number: int
    char_start: int
    char_end: int

    # Inherited from document (denormalized for fast filtering)
    scheme_name: Optional[str] = None
    ministry: Optional[str] = None
    state: Optional[str] = None
    target_income_max: Optional[float] = None
    target_age_min: Optional[int] = None
    target_age_max: Optional[int] = None
    category: Optional[str] = None
    language: str = "en"

    # Embedding versioning (guards against embedding drift)
    embedding_model: str = ""
    embedding_dim: int = 0
    embedded_at: Optional[datetime] = None

    # Dedup hash (SHA-256 of chunk text – future reindex support)
    content_hash: str = ""

    created_at: datetime = Field(default_factory=datetime.utcnow)


class ChunkRecord(BaseModel):
    """
    Single chunk record stored in MongoDB `chunks` collection.
    Child chunks carry the embedding vector; parent chunks store
    the full text for context retrieval.
    """

    chunk_id: str
    text: str
    metadata: ChunkMetadata
    embedding: Optional[List[float]] = None   # stored only on child chunks

    def to_mongo(self) -> Dict[str, Any]:
        d = self.model_dump()
        d["_id"] = self.chunk_id
        return d

    @staticmethod
    def compute_content_hash(text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ─────────────────────────────────────────────────────────────────────────────
# Ingestion Request / Response (used by API layer)
# ─────────────────────────────────────────────────────────────────────────────

class IngestionRequest(BaseModel):
    """Payload accepted by POST /api/v1/documents/upload"""

    scheme_name: Optional[str] = None
    ministry: Optional[str] = None
    state: Optional[str] = None
    target_income_max: Optional[float] = None
    target_age_min: Optional[int] = None
    target_age_max: Optional[int] = None
    category: Optional[str] = None
    language: str = "en"
    source_url: Optional[str] = None


class IngestionResponse(BaseModel):
    doc_id: str
    status: DocumentStatus
    message: str
