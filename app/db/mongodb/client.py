"""
app/db/mongodb/client.py
────────────────────────
Async MongoDB client – Motor-backed singleton.
Call `get_db()` anywhere to obtain the database handle.
"""

from __future__ import annotations

import logging
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.core.config import settings

logger = logging.getLogger(__name__)

_client: AsyncIOMotorClient | None = None


async def connect() -> None:
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(settings.mongodb_uri)
        logger.info("MongoDB connected → %s", settings.mongodb_uri)


async def disconnect() -> None:
    global _client
    if _client:
        _client.close()
        _client = None
        logger.info("MongoDB disconnected.")


def get_db() -> AsyncIOMotorDatabase:
    if _client is None:
        raise RuntimeError("MongoDB client not initialised. Call connect() first.")
    return _client[settings.mongodb_db_name]
