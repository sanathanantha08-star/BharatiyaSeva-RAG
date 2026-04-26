"""
app/services/ingestion/chunking.py
────────────────────────────────────
RCS (Recursive Character Splitter) + Parent-Child chunking strategy.

Strategy
────────
1.  For every cleaned page, apply LangChain's RecursiveCharacterTextSplitter
    to produce PARENT chunks (large context window).
2.  Each parent chunk is split again into smaller CHILD chunks (retrieval units).
3.  Child chunks carry a `parent_chunk_id` reference so we can always
    fetch the full context at retrieval time.
4.  Metadata is stamped on every chunk at creation time.

Chunk sizes (from config)
────────────────────────
  Parent: size=1024, overlap=128
  Child:  size=256,  overlap=32

These values are a good default for government scheme PDFs (~A4, dense text).
Adjust via .env if needed.
"""

from __future__ import annotations

import hashlib
import logging
import uuid
from datetime import datetime
from typing import List, Tuple

from langchain.text_splitter import RecursiveCharacterTextSplitter

from app.core.config import settings
from app.interfaces.ingestion import IChunkingStrategy
from app.models.document import (
    ChunkMetadata,
    ChunkRecord,
    ChunkType,
    ContentType,
    DocumentRecord,
)
from app.services.ingestion.pdf_parser import ParsedPage

logger = logging.getLogger(__name__)

# Separators that respect sentence/paragraph structure in Indian govt PDFs
_SEPARATORS = ["\n\n", "\n", "।", ".", "!", "?", ";", ",", " ", ""]


class RCSParentChildChunker(IChunkingStrategy):
    """
    Recursive Character Splitter with Parent-Child hierarchy.
    """

    def __init__(self) -> None:
        self._parent_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.parent_chunk_size,
            chunk_overlap=settings.parent_chunk_overlap,
            separators=_SEPARATORS,
            length_function=len,
        )
        self._child_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.child_chunk_size,
            chunk_overlap=settings.child_chunk_overlap,
            separators=_SEPARATORS,
            length_function=len,
        )

    # ── Public API ────────────────────────────────────────────────────────────

    def chunk(
        self,
        pages: List[ParsedPage],
        doc_record: DocumentRecord,
    ) -> Tuple[List[ChunkRecord], List[ChunkRecord]]:
        """
        Returns (parent_chunks, child_chunks).
        Tables and image captions are appended as additional child chunks
        with their respective ContentType.
        """
        all_parents: List[ChunkRecord] = []
        all_children: List[ChunkRecord] = []

        for page in pages:
            # ── Text chunks ──────────────────────────────────────────────────
            if page.raw_text.strip():
                parents, children = self._process_text(
                    text=page.raw_text,
                    page_number=page.page_number,
                    doc_record=doc_record,
                    content_type=ContentType.TEXT,
                )
                all_parents.extend(parents)
                all_children.extend(children)

            # ── Table chunks (each table → child only, no parent split) ──────
            for table_text in page.table_texts:
                if table_text.strip():
                    child = self._make_single_chunk(
                        text=table_text,
                        page_number=page.page_number,
                        doc_record=doc_record,
                        content_type=ContentType.TABLE,
                        chunk_type=ChunkType.CHILD,
                        parent_chunk_id=None,
                    )
                    all_children.append(child)

            # ── Image caption chunks ─────────────────────────────────────────
            for caption in page.image_captions:
                if caption.strip():
                    child = self._make_single_chunk(
                        text=caption,
                        page_number=page.page_number,
                        doc_record=doc_record,
                        content_type=ContentType.IMAGE_CAPTION,
                        chunk_type=ChunkType.CHILD,
                        parent_chunk_id=None,
                    )
                    all_children.append(child)

        logger.info(
            "Chunked doc %s → %d parents, %d children",
            doc_record.doc_id,
            len(all_parents),
            len(all_children),
        )
        return all_parents, all_children

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _process_text(
        self,
        text: str,
        page_number: int,
        doc_record: DocumentRecord,
        content_type: ContentType,
    ) -> Tuple[List[ChunkRecord], List[ChunkRecord]]:
        """Split text into parents, then split each parent into children."""
        parent_texts = self._parent_splitter.split_text(text)
        parents: List[ChunkRecord] = []
        children: List[ChunkRecord] = []

        char_cursor = 0
        for p_text in parent_texts:
            p_start = text.find(p_text, char_cursor)
            p_end = p_start + len(p_text)
            char_cursor = p_end

            parent = self._make_single_chunk(
                text=p_text,
                page_number=page_number,
                doc_record=doc_record,
                content_type=content_type,
                chunk_type=ChunkType.PARENT,
                parent_chunk_id=None,
                char_start=p_start,
                char_end=p_end,
            )
            parents.append(parent)

            # Split parent into children
            child_texts = self._child_splitter.split_text(p_text)
            c_cursor = 0
            for c_text in child_texts:
                c_start = p_text.find(c_text, c_cursor)
                c_end = c_start + len(c_text)
                c_cursor = c_end

                child = self._make_single_chunk(
                    text=c_text,
                    page_number=page_number,
                    doc_record=doc_record,
                    content_type=content_type,
                    chunk_type=ChunkType.CHILD,
                    parent_chunk_id=parent.chunk_id,
                    char_start=p_start + c_start,
                    char_end=p_start + c_end,
                )
                children.append(child)

        return parents, children

    def _make_single_chunk(
        self,
        text: str,
        page_number: int,
        doc_record: DocumentRecord,
        content_type: ContentType,
        chunk_type: ChunkType,
        parent_chunk_id: str | None,
        char_start: int = 0,
        char_end: int = 0,
    ) -> ChunkRecord:
        chunk_id = str(uuid.uuid4())
        content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        meta = doc_record.metadata

        metadata = ChunkMetadata(
            doc_id=doc_record.doc_id,
            chunk_id=chunk_id,
            chunk_type=chunk_type,
            parent_chunk_id=parent_chunk_id,
            content_type=content_type,
            page_number=page_number,
            char_start=char_start,
            char_end=char_end,
            # Denormalized document metadata for fast filtering
            scheme_name=meta.scheme_name,
            ministry=meta.ministry,
            state=meta.state,
            target_income_max=meta.target_income_max,
            target_age_min=meta.target_age_min,
            target_age_max=meta.target_age_max,
            category=meta.category,
            language=meta.language,
            content_hash=content_hash,
            created_at=datetime.utcnow(),
        )

        return ChunkRecord(chunk_id=chunk_id, text=text, metadata=metadata)
