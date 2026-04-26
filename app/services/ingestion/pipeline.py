"""
app/services/ingestion/pipeline.py
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import uuid
from pathlib import Path

from app.core.config import settings
from app.interfaces.ingestion import (
    IChunkingStrategy,
    IDocumentRepository,
    IChunkRepository,
    IEmbeddingService,
    IPDFParser,
    ITextCleaner,
    IVectorRepository,
)
from app.models.document import (
    DocumentMetadata,
    DocumentRecord,
    DocumentStatus,
    IngestionRequest,
)
from app.repositories.chunk_repository import MongoChunkRepository
from app.repositories.document_repository import MongoDocumentRepository
from app.repositories.vector_repository import MongoVectorRepository
from app.services.ingestion.chunking import RCSParentChildChunker
from app.services.ingestion.embedding_service import SentenceTransformerEmbeddingService
from app.services.ingestion.pdf_parser import PyMuPDFParser
from app.services.ingestion.text_cleaner import GovPDFTextCleaner

logger = logging.getLogger(__name__)
_semaphore = asyncio.Semaphore(settings.max_concurrent_tasks)


class IngestionPipeline:

    def __init__(
        self,
        parser: IPDFParser | None = None,
        cleaner: ITextCleaner | None = None,
        chunker: IChunkingStrategy | None = None,
        embedder: IEmbeddingService | None = None,
        doc_repo: IDocumentRepository | None = None,
        chunk_repo: IChunkRepository | None = None,
        vector_repo: IVectorRepository | None = None,
    ) -> None:
        self._parser = parser or PyMuPDFParser()
        self._cleaner = cleaner or GovPDFTextCleaner()
        self._chunker = chunker or RCSParentChildChunker()
        self._embedder = embedder or SentenceTransformerEmbeddingService()
        self._doc_repo = doc_repo or MongoDocumentRepository()
        self._chunk_repo = chunk_repo or MongoChunkRepository()
        self._vector_repo = vector_repo or MongoVectorRepository()

    async def ingest(self, pdf_path: Path, request: IngestionRequest) -> str:
        doc_id = str(uuid.uuid4())
        file_bytes = pdf_path.read_bytes()
        file_hash = hashlib.sha256(file_bytes).hexdigest()

        metadata = DocumentMetadata(
            filename=pdf_path.name,
            file_size_bytes=len(file_bytes),
            total_pages=0,
            file_hash=file_hash,
            scheme_name=request.scheme_name,
            ministry=request.ministry,
            state=request.state,
            target_income_max=request.target_income_max,
            target_age_min=request.target_age_min,
            target_age_max=request.target_age_max,
            category=request.category,
            language=request.language,
            source_url=request.source_url,
        )

        doc_record = DocumentRecord(doc_id=doc_id, metadata=metadata)
        await self._doc_repo.upsert(doc_record)
        logger.info("Ingestion queued: doc_id=%s file=%s", doc_id, pdf_path.name)

        asyncio.create_task(
            self._run_pipeline(doc_id, pdf_path, doc_record),
            name=f"ingest-{doc_id}",
        )
        return doc_id

    async def _run_pipeline(self, doc_id: str, pdf_path: Path, doc_record: DocumentRecord) -> None:
        async with _semaphore:
            try:
                await self._doc_repo.update_status(doc_id, DocumentStatus.PROCESSING)

                parsed_pages = await self._parser.parse(pdf_path)
                doc_record.metadata.total_pages = len(parsed_pages)
                await self._doc_repo.upsert(doc_record)

                for page in parsed_pages:
                    page.raw_text = self._cleaner.clean(page.raw_text)

                parent_chunks, child_chunks = self._chunker.chunk(parsed_pages, doc_record)

                await self._chunk_repo.upsert_batch(parent_chunks + child_chunks)

                embedded_children = await self._embed_in_batches(child_chunks)

                await self._vector_repo.upsert_vectors(embedded_children)

                child_ids = [c.chunk_id for c in embedded_children]
                await self._doc_repo.append_chunk_ids(doc_id, child_ids)

                await self._doc_repo.update_status(doc_id, DocumentStatus.COMPLETED)
                logger.info("Ingestion completed: doc_id=%s parents=%d children=%d",
                            doc_id, len(parent_chunks), len(child_chunks))

            except Exception as exc:
                logger.exception("Ingestion failed for doc_id=%s: %s", doc_id, exc)
                await self._doc_repo.update_status(doc_id, DocumentStatus.FAILED, error=str(exc))

    async def _embed_in_batches(self, chunks):
        batch_size = settings.ingestion_batch_size
        results = []
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i: i + batch_size]
            embedded = await self._embedder.embed_chunks(batch)
            results.extend(embedded)
        return results