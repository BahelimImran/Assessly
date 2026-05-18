# Assessly AI

Assessly AI is a full-stack Retrieval-Augmented Generation (RAG) knowledge assistant for uploading PDF documents, indexing them into a vector database, and asking grounded questions against the user's own knowledge base.

The project is built as a production-oriented learning and portfolio system. It includes an Angular frontend, FastAPI backend, Redis-backed job queues, background workers, PostgreSQL metadata persistence, Qdrant vector search, JWT authentication, and Docker Compose deployment files for development and staging/production-style environments.

> Current status: Assessly has a production-grade architecture direction, but it is still under active hardening. See [Production Readiness](#production-readiness-status) and [Roadmap](#roadmap--pending-improvements).

---

## Key Features

Implemented:

- PDF upload and ingestion through a background worker.
- Query answering through a Redis-backed query worker.
- JWT-based authentication with access tokens and refresh-token cookies.
- Guest/demo mode with restricted permissions.
- Per-user document isolation across API, Postgres metadata, Redis jobs, and Qdrant filters.
- Qdrant vector storage with separate parent and child collections.
- Hybrid retrieval over child chunks, followed by parent chunk context assembly.
- SSE progress streams for ingestion and query jobs.
- Duplicate document detection using document hash.
- Safe re-ingestion/replacement flow that keeps old vectors until the new upload succeeds.
- PostgreSQL metadata for users, documents, upload sessions, ingestion jobs, refresh tokens, and audit events.
- Redis Streams for ingestion and query queues.
- Upload size limits, query/upload rate limits, and LLM concurrency limits.
- Docker Compose files for development infrastructure and production-style services.
- Health endpoints for Redis, Qdrant, and Postgres.

Not yet fully production-hardened:

- CI test suite coverage is still limited.
- Frontend build, route guards, and auth services need cleanup.
- Structured logging and monitoring are basic.
- Migration automation and backup/restore procedures need production polish.
- LLM concurrency currently protects the model, but queued waiting behavior should be improved.

---

## Architecture

```text
Angular Frontend
  |
  | REST + SSE
  v
FastAPI Backend
  |
  | Auth, validation, metadata, queue creation
  v
Redis Streams
  |                     |
  | ingestion_jobs       | query_jobs
  v                     v
Ingestion Worker       Query Worker
  |                     |
  | parse, chunk, embed  | retrieve, build prompt, call LLM
  v                     v
Qdrant                 Ollama / model provider
  |
PostgreSQL metadata tracks users, documents, sessions, jobs, tokens, and audit events.
```

Development setup currently runs:

- Angular frontend locally.
- FastAPI backend locally.
- Redis, Qdrant, Postgres, ingestion worker, and query worker through Docker Compose.

Production-style Compose can run:

- backend
- frontend
- worker
- query_worker
- redis
- qdrant
- postgres

---

## Tech Stack

Frontend:

- Angular 21
- TypeScript
- RxJS

Backend:

- Python 3.11
- FastAPI
- Uvicorn / Gunicorn
- Pydantic

Data and infrastructure:

- PostgreSQL
- SQLAlchemy
- Alembic
- Redis
- Redis Streams
- Qdrant
- Docker / Docker Compose

RAG and model layer:

- Ollama-compatible model API
- Configurable embedding model
- Configurable LLM model
- Docling-based PDF parsing
- FastEmbed BM25 sparse vectors
- Qdrant dense + sparse retrieval

Authentication and security:

- JWT access tokens
- HttpOnly refresh-token cookie
- Password hashing with Passlib/Bcrypt
- Role-based access helpers for user, admin, and guest/demo flows

---

## RAG Pipeline Flow

```text
PDF Upload
  -> file validation and size checks
  -> document hash calculation
  -> Postgres metadata creation
  -> Redis ingestion job
  -> ingestion worker
  -> Docling document parsing
  -> parent and child chunk creation
  -> dense embeddings through Ollama
  -> sparse BM25 vectors through FastEmbed
  -> Qdrant parent/child upsert
  -> Postgres document/session/job status update
```

Query flow:

```text
User question
  -> FastAPI creates query_job_id
  -> Redis query job
  -> query worker
  -> user-filtered Qdrant retrieval
  -> active upload-session filtering
  -> parent chunk context assembly
  -> prompt construction
  -> Ollama generation
  -> Redis job result/status
  -> frontend receives result through SSE/polling
```

---

## Ingestion Flow

The upload endpoint validates the authenticated user, applies upload rate limits, streams the PDF to disk in chunks, validates size and page count, computes a document hash, and creates durable metadata before queueing the worker job.

Important behavior:

- The backend derives `user_id` from the JWT token.
- Browser-provided `user_id` is not trusted for protected upload flow.
- Duplicate files are detected by `user_id + document_hash`.
- If a duplicate is found, the frontend can ask the user to confirm safe replacement.
- The worker stores new vectors first.
- Previous active upload-session vectors are deleted only after the new ingestion succeeds.
- Failed ingestion updates Redis and Postgres status.

Main files:

- `backend/app/api/ingest.py`
- `backend/app/worker.py`
- `backend/app/services/job_queue.py`
- `backend/app/services/job_manager.py`
- `backend/app/services/metadata_repository.py`
- `backend/app/services/rag_service.py`

---

## Query Flow

The query endpoint no longer performs the full RAG pipeline inside the FastAPI request. It creates a query job and returns immediately.

```text
POST /query
  -> create query_job_id
  -> store Redis query status
  -> enqueue query_jobs stream
  -> return queued response

query_worker
  -> consume query job
  -> retrieve user-filtered chunks
  -> generate answer
  -> store completed/failed status
  -> publish query_logs:{query_job_id}
```

Main files:

- `backend/app/api/query.py`
- `backend/app/query_worker.py`
- `backend/app/services/query_queue.py`
- `backend/app/services/query_job_manager.py`
- `backend/app/services/rag_service.py`
- `backend/app/services/pubsub_logger.py`

---

## Redis And Worker Architecture

Redis is used for:

- ingestion job live status
- query job live status
- ingestion logs via Pub/Sub
- query logs via Pub/Sub
- ingestion queue through Redis Streams
- query queue through Redis Streams
- rate limiting counters
- LLM concurrency counters

Queues:

- `ingestion_jobs` stream consumed by `app.worker`
- `query_jobs` stream consumed by `app.query_worker`

The worker code uses Redis consumer groups and attempts to reclaim stale jobs with `XAUTOCLAIM`, reducing the chance of silent job loss after a worker crash.

---

## PostgreSQL Usage

PostgreSQL stores durable application metadata:

- users
- refresh tokens
- documents
- upload sessions
- ingestion jobs
- audit events

This keeps ownership, job history, and document lifecycle outside Qdrant. Qdrant remains the vector retrieval engine, while Postgres is the system of record for users and document metadata.

Migrations are managed with Alembic:

```bash
cd backend
alembic upgrade head
```

For production, `AUTO_CREATE_DB_TABLES=false` should be used and migrations should run as an explicit deployment step.

---

## Qdrant Usage

Qdrant stores document chunks in two collections:

- `parent_chunks`: parent/section-level payload records
- `child_chunks`: searchable child chunks with dense and sparse vectors

Payload metadata includes:

- `user_id`
- `document_id`
- `document_hash`
- `upload_session_id`
- `source_file`
- `section_title`
- `content_type`

User and upload-session filters are applied during retrieval so one user's private documents are not mixed with another user's answers.

---

## Multi-User Isolation

Assessly currently enforces user isolation in several layers:

- JWT token determines the server-side user identity.
- Upload, delete, ingestion job, query job, and SSE endpoints check ownership.
- Postgres documents belong to a user record.
- Qdrant payloads include `user_id`.
- Retrieval filters by `user_id` and active upload sessions.
- Guest users can query demo content but cannot upload or delete documents.

Important limitation:

- The frontend currently stores the access token in `localStorage` for development convenience. For stronger production hardening, move toward a safer token strategy and add CSRF protection for cookie-backed refresh/logout flows.

---

## API Endpoints

Auth:

- `POST /auth/register`
- `POST /auth/login`
- `POST /auth/guest`
- `POST /auth/refresh`
- `POST /auth/logout`
- `GET /auth/me`

Ingestion:

- `POST /ingest`
- `GET /ingest/jobs/{job_id}`
- `GET /ingest/stream/{job_id}`

Query:

- `POST /query`
- `GET /query/jobs/{query_job_id}`
- `GET /query/jobs/{query_job_id}/stream`

Knowledge base:

- `GET /knowledge-base/files`
- `DELETE /knowledge-base/files/{document_id}`

Admin:

- `GET /admin/health`
- `GET /admin/users`
- `GET /admin/jobs/failed`

Health:

- `GET /health/redis`
- `GET /health/qdrant`
- `GET /health/postgres`

---

## Environment Variables

Common backend variables:

```env
FRONTEND_URL=http://localhost:4200
API_DOMAIN=http://localhost:8000

DATABASE_URL=postgresql+psycopg://assessly:assessly@localhost:5432/assessly
REDIS_URL=redis://localhost:6379/0
QDRANT_URL=http://localhost:6333

OLLAMA_BASE_URL=http://localhost:11434
EMBED_PROVIDER=ollama
EMBED_MODEL=bge-m3
LLM_PROVIDER=ollama
LLM_MODEL=qwen2.5:7b

JWT_SECRET_KEY=replace-with-a-strong-secret
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
REFRESH_COOKIE_SECURE=false
REFRESH_COOKIE_SAMESITE=lax

MAX_UPLOAD_SIZE_MB=25
MAX_ACTIVE_JOBS_PER_USER=3
QUERY_RATE_LIMIT_PER_MINUTE=30
UPLOAD_RATE_LIMIT_PER_MINUTE=5
GUEST_QUERY_RATE_LIMIT_PER_MINUTE=5
RATE_LIMIT_WINDOW_SECONDS=60
LLM_CONCURRENCY_LIMIT=2

AUTO_CREATE_DB_TABLES=true
```

Production notes:

- Do not commit real `.env` files or secrets.
- Use a strong `JWT_SECRET_KEY`.
- Set `REFRESH_COOKIE_SECURE=true` behind HTTPS.
- Set `AUTO_CREATE_DB_TABLES=false`.
- Run Alembic migrations before starting production services.

---

## Setup Instructions

### 1. Clone

```bash
git clone https://github.com/your-username/assessly.git
cd Assessly
```

### 2. Start Infrastructure For Development

The development Compose file is intended for independent infrastructure and workers while the frontend and FastAPI backend can run locally.

```bash
docker compose up -d redis qdrant postgres worker query_worker
```

### 3. Backend Setup

```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

The backend runs at:

```text
http://localhost:8000
```

### 4. Frontend Setup

```bash
cd frontend
npm install
npm start
```

The frontend runs at:

```text
http://localhost:4200
```

### 5. Ollama / Model Runtime

Assessly expects an Ollama-compatible API configured by `OLLAMA_BASE_URL`.

Example local models used by the current configuration:

```bash
ollama pull bge-m3
ollama pull qwen2.5:7b
```

Model choice is configurable through environment variables.

---

## Docker Compose Instructions

Development infrastructure:

```bash
docker compose up -d redis qdrant postgres worker query_worker
```

Production-style stack:

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

Production migration step:

```bash
docker compose -f docker-compose.prod.yml run --rm backend alembic upgrade head
```

Useful checks:

```bash
docker compose ps
docker compose logs -f worker
docker compose logs -f query_worker
docker compose logs -f redis
docker compose logs -f qdrant
docker compose logs -f postgres
```

---

## How To Use

1. Register or log in.
2. Upload a PDF.
3. Watch ingestion progress through the UI.
4. Ask a question.
5. Query job progress appears while the worker retrieves context and generates the answer.
6. View or delete your own knowledge-base files.

Guest mode:

- Guest users can use demo/query flows.
- Guest users cannot upload or delete private documents.

---

## Production Readiness Status

Implemented foundations:

- Worker-based ingestion.
- Worker-based query execution.
- Redis Streams queues.
- Postgres metadata persistence.
- Qdrant vector storage.
- JWT authentication.
- Per-user isolation.
- Health endpoints.
- Docker Compose services.
- Alembic migrations.
- Basic rate limits and upload limits.

Still required before real production:

- CI tests for backend, frontend, workers, auth, upload, query, and migration flows.
- Production migration automation.
- Stronger frontend auth architecture with interceptors/guards.
- Remove debug `print()` and `console.log()` output.
- Structured logging and centralized log collection.
- Metrics and alerting for Redis queues, worker failures, Qdrant health, Postgres health, API latency, and LLM failures.
- Safer LLM concurrency behavior where excess work waits instead of failing.
- Backup and restore strategy for Postgres, Qdrant, Redis, and uploaded files.
- HTTPS reverse proxy and secure production secret management.
- Load testing for expected concurrent usage.

---

## Roadmap / Pending Improvements

High priority:

- Add automated test suite and GitHub Actions CI.
- Add production migration runner or documented release step.
- Replace remaining debug logs with structured logging.
- Improve LLM concurrency queue behavior.
- Add retry/dead-letter handling for failed query jobs.
- Harden token storage and cookie/CSRF handling.
- Add frontend API services, auth interceptor, and route guards.

Medium priority:

- Add admin UI for failed jobs, users, and cleanup tasks.
- Add scheduled cleanup for orphan files and orphan Qdrant points.
- Add observability stack such as Prometheus, Grafana, Loki, or Langfuse.
- Add demo document seeding flow for guest users.
- Add better citations and source display in the UI.

Future:

- Managed/cloud deployment guide.
- Horizontal worker scaling guide.
- External model provider support.
- OCR and image-heavy PDF support.
- More advanced reranking and confidence scoring.

---

## Repository Structure

```text
backend/
  app/
    api/                 FastAPI routers
    core/                config and shared clients
    db/                  Postgres and Qdrant clients
    models/              Pydantic and SQLAlchemy models
    services/            auth, queues, metadata, RAG, retrieval, parsing
    worker.py            ingestion worker
    query_worker.py      query worker
  alembic/               database migrations
  Dockerfile
  requirements.txt

frontend/
  src/app/features/      Angular UI components
  Dockerfile
  package.json

docker-compose.yml       development infrastructure/workers
docker-compose.prod.yml  production-style stack
```

---

## Author

Imran Bahelim

Lead Fullstack + AI Engineer

