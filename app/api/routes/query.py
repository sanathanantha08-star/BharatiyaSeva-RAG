"""
app/api/routes/query.py
────────────────────────
POST /api/v1/query  – QnA over ingested scheme documents.

FUTURE IMPLEMENTATION:
  - User eligibility profile (income, age, region) as query context
  - Hybrid retrieval (BM25 + vector) with RRF
  - Query rewriting / decomposition
  - Query routing / classifier
  - Contextual compression + FlashRank reranker
  - Lost-in-middle context ordering
  - Structured prompt with context window budgeting
"""

from fastapi import APIRouter

router = APIRouter()


@router.post("/", summary="Ask a question (stub)")
async def query_documents():
    return {"message": "Query endpoint – to be implemented."}
