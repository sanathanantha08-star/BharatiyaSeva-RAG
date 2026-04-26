"""
app/repositories/vector_repository.py
──────────────────────────────────────
Concrete implementation of IVectorRepository using MongoDB Atlas
Vector Search (free tier, local).

MongoDB Atlas Vector Search stores vectors as a field on a regular
document inside the same chunks collection. The vector index is created
separately (see app/db/mongodb/indexes.py or the Atlas UI).

Vector Index definition (create once in Atlas / mongosh):
─────────────────────────────────────────────────────────
db.chunks.createIndex(
  { "embedding": "vectorSearch" },
  {
    name: "vector_index",
    vectorSearchOptions: {
      numDimensions: 384,           // match EMBEDDING_DIM in .env
      similarity: "cosine",
      type: "hnsw"
    }
  }
)
"""

from __future__ import annotations

import logging
from typing import List

from pymongo import UpdateOne

from app.core.config import settings
from app.db.mongodb.client import get_db
from app.interfaces.ingestion import IVectorRepository
from app.models.document import ChunkRecord

logger = logging.getLogger(__name__)


class MongoVectorRepository(IVectorRepository):
    """
    Stores the embedding vector directly on the chunk document in MongoDB.
    This avoids a separate vector DB and keeps the free-tier footprint small.
    """

    def _col(self):
        return get_db()[settings.mongodb_collection_chunks]

    async def upsert_vectors(self, chunks: List[ChunkRecord]) -> None:
        """
        Writes / updates the `embedding` field on each child chunk document
        that already exists in the chunks collection.
        """
        if not chunks:
            return

        operations = [
            UpdateOne(
                {"_id": c.chunk_id},
                {
                    "$set": {
                        "embedding": c.embedding,
                        "metadata.embedding_model": c.metadata.embedding_model,
                        "metadata.embedding_dim": c.metadata.embedding_dim,
                        "metadata.embedded_at": c.metadata.embedded_at,
                    }
                },
                upsert=False,  # chunk must already exist
            )
            for c in chunks
            if c.embedding is not None
        ]

        if not operations:
            logger.warning("upsert_vectors called but no chunks had embeddings.")
            return

        result = await self._col().bulk_write(operations, ordered=False)
        logger.debug(
            "Vector upsert: matched=%d modified=%d",
            result.matched_count,
            result.modified_count,
        )
