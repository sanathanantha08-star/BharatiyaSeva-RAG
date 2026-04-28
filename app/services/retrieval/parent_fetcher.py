from __future__ import annotations
import logging
from typing import List
from app.db.mongodb.client import get_db
from app.core.config import settings
from app.models.retrieval import RetrievedChunk

logger = logging.getLogger(__name__)


class ParentFetcher:
    """
    For each retrieved child chunk, fetches the parent chunk text
    and attaches it as parent_text. This is what gets sent to the LLM.
    """

    async def fetch(self, chunks: List[RetrievedChunk]) -> List[RetrievedChunk]:
        col = get_db()[settings.mongodb_collection_chunks]

        parent_ids = list({
            c.metadata.get("parent_chunk_id")
            for c in chunks
            if c.metadata.get("parent_chunk_id")
        })

        if not parent_ids:
            return chunks

        parents = {}
        async for doc in col.find({"_id": {"$in": parent_ids}}, {"text": 1}):
            parents[str(doc["_id"])] = doc["text"]

        for chunk in chunks:
            pid = chunk.metadata.get("parent_chunk_id")
            if pid and pid in parents:
                chunk.parent_text = parents[pid]

        logger.debug("ParentFetcher resolved %d parents", len(parents))
        return chunks