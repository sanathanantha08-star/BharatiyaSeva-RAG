"""
app/db/mongodb/indexes.py
─────────────────────────
Creates all MongoDB indexes on startup — both regular and vector search.
Safe to call every time the app boots (idempotent).
"""

import logging
from pymongo import ASCENDING, IndexModel
from app.db.mongodb.client import get_db
from app.core.config import settings

logger = logging.getLogger(__name__)


async def create_indexes() -> None:
    db = get_db()

    # ── documents collection ──────────────────────────────────────────────────
    doc_col = db[settings.mongodb_collection_documents]
    doc_indexes = [
        IndexModel([("metadata.file_hash", ASCENDING)], name="idx_doc_file_hash"),
        IndexModel([("metadata.state", ASCENDING)],     name="idx_doc_state"),
        IndexModel([("metadata.category", ASCENDING)],  name="idx_doc_category"),
        IndexModel([("status", ASCENDING)],             name="idx_doc_status"),
    ]
    await doc_col.create_indexes(doc_indexes)
    logger.info("Documents collection indexes ensured.")

    # ── chunks collection — regular indexes ───────────────────────────────────
    chunk_col = db[settings.mongodb_collection_chunks]
    chunk_indexes = [
        IndexModel([("metadata.doc_id", ASCENDING)],          name="idx_chunk_doc_id"),
        IndexModel([("metadata.chunk_type", ASCENDING)],      name="idx_chunk_type"),
        IndexModel([("metadata.parent_chunk_id", ASCENDING)], name="idx_chunk_parent"),
        IndexModel([("metadata.content_hash", ASCENDING)],    name="idx_chunk_hash"),
        IndexModel([("metadata.page_number", ASCENDING)],     name="idx_chunk_page"),
        IndexModel([("metadata.state", ASCENDING)],           name="idx_chunk_state"),
        IndexModel([("metadata.category", ASCENDING)],        name="idx_chunk_category"),
    ]
    await chunk_col.create_indexes(chunk_indexes)
    logger.info("Chunks collection indexes ensured.")

    # ── chunks collection — vector search index ───────────────────────────────
    # MongoDB Atlas Vector Search index must be created via the Atlas UI or
    # mongosh — it cannot be created via the driver API.
    #
    # Run this ONCE in mongosh after the app has started:
    #
    # use bharatiya_seva
    # db.chunks.createIndex(
    #   { embedding: "vectorSearch" },
    #   {
    #     name: "vector_index",
    #     vectorSearchOptions: {
    #       numDimensions: 384,
    #       similarity: "cosine",
    #       type: "hnsw"
    #     }
    #   }
    # )
    #
    # Once created, $vectorSearch queries will use it automatically.
    logger.info(
        "NOTE: Vector search index must be created manually in mongosh. "
        "See comment above for the exact command."
    )