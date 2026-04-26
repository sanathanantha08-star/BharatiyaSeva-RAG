"""
app/api/routes/documents.py
"""
from __future__ import annotations

import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from app.core.config import settings
from app.models.document import IngestionRequest, IngestionResponse, DocumentStatus
from app.repositories.chunk_repository import MongoChunkRepository
from app.repositories.document_repository import MongoDocumentRepository
from app.repositories.vector_repository import MongoVectorRepository
from app.services.ingestion.chunking import RCSParentChildChunker
from app.services.ingestion.embedding_service import SentenceTransformerEmbeddingService
from app.services.ingestion.pdf_parser import PyMuPDFParser
from app.services.ingestion.pipeline import IngestionPipeline
from app.services.ingestion.text_cleaner import GovPDFTextCleaner

router = APIRouter()

_pipeline = IngestionPipeline(
    parser=PyMuPDFParser(),
    cleaner=GovPDFTextCleaner(),
    chunker=RCSParentChildChunker(),
    embedder=SentenceTransformerEmbeddingService(),
    doc_repo=MongoDocumentRepository(),
    chunk_repo=MongoChunkRepository(),
    vector_repo=MongoVectorRepository(),
)

_doc_repo = MongoDocumentRepository()


@router.post("/upload", response_model=IngestionResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    file: UploadFile = File(...),
    scheme_name: str | None = Form(None),
    ministry: str | None = Form(None),
    state: str | None = Form(None),
    target_income_max: float | None = Form(None),
    target_age_min: int | None = Form(None),
    target_age_max: int | None = Form(None),
    category: str | None = Form(None),
    language: str = Form("en"),
    source_url: str | None = Form(None),
):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = upload_dir / f"{uuid.uuid4()}_{file.filename}"

    with pdf_path.open("wb") as f:
        shutil.copyfileobj(file.file, f)

    request = IngestionRequest(
        scheme_name=scheme_name,
        ministry=ministry,
        state=state,
        target_income_max=target_income_max,
        target_age_min=target_age_min,
        target_age_max=target_age_max,
        category=category,
        language=language,
        source_url=source_url,
    )

    doc_id = await _pipeline.ingest(pdf_path, request)
    return IngestionResponse(doc_id=doc_id, status=DocumentStatus.PENDING,
                             message="Document accepted. Ingestion running in background.")


@router.get("/{doc_id}")
async def get_document(doc_id: str):
    record = await _doc_repo.get_by_id(doc_id)
    if not record:
        raise HTTPException(status_code=404, detail="Document not found.")
    return record


@router.get("/")
async def list_documents():
    return {"message": "List endpoint – implement pagination here."}


@router.delete("/{doc_id}")
async def delete_document(doc_id: str):
    return {"message": f"Delete for {doc_id} – stub."}