from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.logging import setup_logging
from app.db.mongodb.client import connect, disconnect
from app.db.mongodb.indexes import create_indexes
from app.api.routes import documents, query, chat, health
from app.api.routes import documents, query, chat, health, user 


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    await connect()
    await create_indexes()
    yield
    await disconnect()


def create_app() -> FastAPI:
    app = FastAPI(
        title="BharatiyaSeva",
        description="Multimodal RAG for Government Scheme Discovery",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.include_router(user.router, prefix="/api/v1/user", tags=["user"])

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router, prefix="/api/v1", tags=["health"])
    app.include_router(documents.router, prefix="/api/v1/documents", tags=["documents"])
    app.include_router(query.router, prefix="/api/v1/query", tags=["query"])
    app.include_router(chat.router, prefix="/api/v1/chat", tags=["chat"])

    return app


app = create_app()