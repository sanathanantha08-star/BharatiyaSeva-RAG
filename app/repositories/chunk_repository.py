"""
app/repositories/chunk_repository.py
─────────────────────────────────────
Concrete MongoDB implementation of IChunkRepository.
Stores both parent and child ChunkRecord objects.
"""

from __future__ import annotations

import logging
from typing import List

from pymongo import ReplaceOne

from app.core.config import settings
from app.db.mongodb.client import get_db
from app.interfaces.ingestion import IChunkRepository
from app.models.document import ChunkRecord

logger = logging.getLogger(__name__)


class MongoChunkRepository(IChunkRepository):

    def _col(self):
        return get_db()[settings.mongodb_collection_chunks]

    async def upsert_batch(self, chunks: List[ChunkRecord]) -> None:
        if not chunks:
            return
        operations = [
            ReplaceOne({"_id": c.chunk_id}, c.to_mongo(), upsert=True)
            for c in chunks
        ]
        result = await self._col().bulk_write(operations, ordered=False)
        logger.debug(
            "Chunk upsert: upserted=%d modified=%d",
            result.upserted_count,
            result.modified_count,
        )

    async def get_by_id(self, chunk_id: str) -> ChunkRecord | None:
        raw = await self._col().find_one({"_id": chunk_id})
        if raw is None:
            return None
        raw["chunk_id"] = raw.pop("_id")
        return ChunkRecord(**raw)

    async def get_parent(self, parent_chunk_id: str) -> ChunkRecord | None:
        return await self.get_by_id(parent_chunk_id)

    async def delete_by_doc_id(self, doc_id: str) -> int:
        result = await self._col().delete_many({"metadata.doc_id": doc_id})
        logger.info("Deleted %d chunks for doc_id=%s", result.deleted_count, doc_id)
        return result.deleted_count
