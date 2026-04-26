# BharatiyaSeva – Multimodal RAG for Government Scheme Discovery

Eligibility-driven QnA over Indian government welfare scheme PDFs.

---

## What's Implemented (Today)

| Layer | Component | Status |
|---|---|---|
| Parser | PyMuPDF – text, tables, image captions | ✅ |
| Cleaner | GovPDFTextCleaner – unicode, noise, page numbers | ✅ |
| Chunking | RCS Parent-Child (1024/128 → 256/32) | ✅ |
| Metadata | Scheme-level + positional stamps on every chunk | ✅ |
| Storage | MongoDB `documents` + `chunks` collections | ✅ |
| Vectors | MongoDB Atlas Vector Search (inline embedding field) | ✅ |
| Embeddings | sentence-transformers/all-MiniLM-L6-v2 (free, local) | ✅ |
| Pipeline | Async batched ingestion with asyncio.Semaphore | ✅ |
| API | POST /upload, GET /documents/{id} | ✅ |

---

## Local Setup

### 1 – Install MongoDB Community (free, local)

**macOS**
```bash
brew tap mongodb/brew
brew install mongodb-community@7.0
brew services start mongodb-community@7.0
```

**Ubuntu / Debian**
```bash
sudo apt-get install -y mongodb
sudo systemctl start mongod
```

**Windows** – Download installer from https://www.mongodb.com/try/download/community

Verify connection:
```bash
mongosh "mongodb://localhost:27017"
```

### 2 – Create the Vector Search Index

MongoDB Atlas Vector Search requires an index on the `embedding` field.
Run this once in mongosh after the app has created the collection:

```js
use bharatiya_seva

db.chunks.createIndex(
  { "embedding": "vectorSearch" },
  {
    name: "vector_index",
    vectorSearchOptions: {
      numDimensions: 384,
      similarity: "cosine",
      type: "hnsw"
    }
  }
)
```

> Note: Atlas Vector Search on local MongoDB requires MongoDB 7.0+ with the
> Atlas CLI or a local Atlas deployment. Alternatively, swap `MongoVectorRepository`
> for a Chroma / Qdrant local adapter (stub in `app/db/vectordb/client.py`).

### 3 – Python Environment

```bash
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 4 – Environment Variables

Copy `.env` and fill in your values:

```bash
cp .env .env.local
# Edit .env.local – at minimum set LLM_API_KEY if you want LLM calls
```

Key variables:

| Variable | Default | Description |
|---|---|---|
| `MONGODB_URI` | `mongodb://localhost:27017` | Local MongoDB |
| `MONGODB_DB_NAME` | `bharatiya_seva` | Database name |
| `EMBEDDING_MODEL_NAME` | `sentence-transformers/all-MiniLM-L6-v2` | Free HF model |
| `PARENT_CHUNK_SIZE` | `1024` | Parent chunk token size |
| `CHILD_CHUNK_SIZE` | `256` | Child chunk token size |
| `INGESTION_BATCH_SIZE` | `10` | Embedding batch size |
| `MAX_CONCURRENT_TASKS` | `4` | Parallel ingestion jobs |
| `LLM_API_KEY` | *(empty)* | Groq / Together AI key |

### 5 – Run the App

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API docs: http://localhost:8000/docs

### 6 – Ingest a PDF

```bash
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -F "file=@/path/to/scheme.pdf" \
  -F "scheme_name=PM Kisan" \
  -F "ministry=Agriculture" \
  -F "state=All India" \
  -F "category=Agriculture" \
  -F "target_income_max=200000"
```

Check status:
```bash
curl http://localhost:8000/api/v1/documents/{doc_id}
```

---

## Project Structure

```
bharatiya_seva/
├── .env                          # Raw env values (never commit)
├── requirements.txt
├── app/
│   ├── main.py                   # FastAPI app + lifespan hooks
│   ├── core/
│   │   ├── config.py             # Settings (reads .env)
│   │   └── logging.py
│   ├── api/routes/
│   │   ├── documents.py          # Upload + status endpoints ✅
│   │   ├── query.py              # QnA endpoint (stub)
│   │   ├── chat.py               # Chat history (stub)
│   │   └── health.py
│   ├── models/
│   │   ├── document.py           # DocumentRecord, ChunkRecord, enums ✅
│   │   ├── chat.py               # (stub)
│   │   └── query.py              # (stub)
│   ├── interfaces/
│   │   └── ingestion.py          # ABCs for all pipeline components ✅
│   ├── db/mongodb/
│   │   ├── client.py             # Motor async client singleton ✅
│   │   └── indexes.py            # Index creation on startup ✅
│   ├── db/vectordb/
│   │   └── client.py             # (stub – future dedicated vector DB)
│   ├── repositories/
│   │   ├── document_repository.py ✅
│   │   ├── chunk_repository.py    ✅
│   │   ├── vector_repository.py   ✅
│   │   └── chat_repository.py     (stub)
│   └── services/
│       ├── ingestion/
│       │   ├── pipeline.py        # Orchestrator ✅
│       │   ├── pdf_parser.py      # PyMuPDF ✅
│       │   ├── text_cleaner.py    # Gov PDF cleaner ✅
│       │   ├── chunking.py        # RCS parent-child ✅
│       │   ├── embedding_service.py # HF sentence-transformers ✅
│       │   └── dedup.py           # (stub – future delta reindex)
│       ├── retrieval/
│       │   ├── hybrid_retriever.py (stub)
│       │   ├── reranker.py         (stub)
│       │   ├── query_processor.py  (stub)
│       │   └── cache.py            (stub)
│       └── llm/
│           └── llm_service.py      (stub)
```

---

## Chunk Size Rationale

| Level | Size | Overlap | Why |
|---|---|---|---|
| Parent | 1024 chars | 128 | Full context for answer generation (~200 tokens) |
| Child | 256 chars | 32 | Retrieval unit – tight semantic match (~50 tokens) |

Government scheme PDFs are dense with eligibility criteria, benefit amounts,
and application steps packed into short paragraphs. 256-char children give
precise retrieval; 1024-char parents give complete context to the LLM.

---

## Free Stack

| Component | Tool | Cost |
|---|---|---|
| PDF parsing | PyMuPDF | Free / open-source |
| Embeddings | all-MiniLM-L6-v2 | Free / local |
| Document DB | MongoDB Community 7 | Free / local |
| Vector Search | MongoDB Atlas Vector (local) | Free |
| LLM | Groq (llama3-8b) | Free tier |
| Framework | FastAPI + LangChain | Open-source |
