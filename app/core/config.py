"""
app/core/config.py
──────────────────
Central configuration – reads every value from .env via pydantic-settings.
All other modules import from here; never read os.environ directly.
"""

from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── MongoDB ──────────────────────────────────────────────────────────────
    mongodb_uri: str = Field("mongodb://localhost:27017")
    mongodb_db_name: str = Field("bharatiya_seva")
    mongodb_collection_documents: str = Field("documents")
    mongodb_collection_chunks: str = Field("chunks")
    mongodb_vector_index_name: str = Field("vector_index")
    vector_embedding_dimension: int = Field(384)

    # ── Embeddings ───────────────────────────────────────────────────────────
    embedding_model_name: str = Field("sentence-transformers/all-MiniLM-L6-v2")
    embedding_device: str = Field("cpu")

    # ── Chunking ─────────────────────────────────────────────────────────────
    parent_chunk_size: int = Field(1024)
    parent_chunk_overlap: int = Field(128)
    child_chunk_size: int = Field(256)
    child_chunk_overlap: int = Field(32)

    # ── Ingestion Pipeline ───────────────────────────────────────────────────
    ingestion_batch_size: int = Field(10)
    max_concurrent_tasks: int = Field(4)
    upload_dir: str = Field("./uploads")
    processed_dir: str = Field("./processed")

    # ── LLM ──────────────────────────────────────────────────────────────────
    llm_provider: str = Field("groq")
    llm_api_key: str = Field("")
    llm_model_name: str = Field("llama3-8b-8192")
    llm_temperature: float = Field(0.0)
    llm_max_tokens: int = Field(1024)

    # ── Redis (future) ───────────────────────────────────────────────────────
    redis_url: str = Field("redis://localhost:6379")

    # ── LangSmith (future) ───────────────────────────────────────────────────
    langchain_api_key: str = Field("")
    langchain_project: str = Field("bharatiya-seva")

    # ── App ──────────────────────────────────────────────────────────────────
    app_env: str = Field("development")
    app_host: str = Field("0.0.0.0")
    app_port: int = Field(8000)
    log_level: str = Field("INFO")


@lru_cache()
def get_settings() -> Settings:
    """Return a cached singleton Settings instance."""
    return Settings()


settings = get_settings()
