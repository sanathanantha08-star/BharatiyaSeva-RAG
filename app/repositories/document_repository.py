"""
app/repositories/document_repository.py
────────────────────────────────────────
Concrete MongoDB implementation of IDocumentRepository.
"""

from __future__ import annotations

import logging
from datetime import datetime

from app.core.config import settings
from app.db.mongodb.client import get_db
from app.interfaces.ingestion import IDocumentRepository
from app.models.document import DocumentRecord, DocumentStatus

logger = logging.getLogger(__name__)


class MongoDocumentRepository(IDocumentRepository):

    def _col(self):
        return get_db()[settings.mongodb_collection_documents]

    async def upsert(self, record: DocumentRecord) -> None:
        await self._col().replace_one(
            {"_id": record.doc_id},
            record.to_mongo(),
            upsert=True,
        )
        logger.debug("Upserted document record: %s", record.doc_id)

    async def get_by_id(self, doc_id: str) -> DocumentRecord | None:
        raw = await self._col().find_one({"_id": doc_id})
        if raw is None:
            return None
        raw["doc_id"] = raw.pop("_id")
        return DocumentRecord(**raw)

    async def update_status(
        self,
        doc_id: str,
        status: DocumentStatus,
        error: str = "",
    ) -> None:
        update: dict = {"$set": {"status": status.value}}
        if status == DocumentStatus.PROCESSING:
            update["$set"]["processing_started_at"] = datetime.utcnow()
        elif status in (DocumentStatus.COMPLETED, DocumentStatus.FAILED):
            update["$set"]["processing_completed_at"] = datetime.utcnow()
        if error:
            update["$set"]["error_message"] = error
        await self._col().update_one({"_id": doc_id}, update)
        logger.debug("Updated document %s → status=%s", doc_id, status)

    async def append_chunk_ids(self, doc_id: str, chunk_ids: list[str]) -> None:
        await self._col().update_one(
            {"_id": doc_id},
            {"$addToSet": {"chunk_ids": {"$each": chunk_ids}}},
        )
