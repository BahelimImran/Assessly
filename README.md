# 🧠 Assessly AI — Enterprise RAG Knowledge Assistant

Assessly AI is a production-oriented Retrieval-Augmented Generation (RAG) knowledge assistant that transforms PDFs into intelligent, searchable knowledge systems.

Users can upload documents, process them through a scalable AI pipeline, and ask grounded, context-aware questions using semantic retrieval and LLM-powered reasoning.

Built with a modern full-stack architecture, Assessly focuses not only on AI capabilities — but also on the real engineering challenges involved in building production-grade RAG systems.

---

🎥 Demo Video:  
https://www.linkedin.com/feed/update/urn:li:activity:7453663316465422337/

---

## 🏗️ Architecture Overview

<img width="1672" height="941" alt="Assessly" src="https://github.com/user-attachments/assets/fb4f1a06-04ee-4c9e-800b-e5417eb93247" />


---

## 🚀 Key Features

### 📄 Intelligent Document Processing

- Upload and process PDF documents
- Layout-aware document parsing
- Semantic + section-aware chunking
- Parent-child chunk architecture
- Duplicate document detection
- Safe re-ingestion flow

### 🧠 Advanced RAG Pipeline

- Context-aware question answering
- Hybrid retrieval using dense + sparse search
- Parent-context reconstruction
- Metadata-aware retrieval
- Grounded answer generation
- User-isolated retrieval pipeline

### ⚡ Production-Oriented Architecture

- Redis Streams job queues
- Background ingestion workers
- Background query workers
- SSE live progress streaming
- PostgreSQL metadata persistence
- Durable job tracking
- Multi-user isolation

### 🔐 Authentication & Security

- JWT authentication
- Refresh-token support
- Guest/demo mode
- Per-user document isolation
- Upload/query rate limiting
- LLM concurrency limiting

### 🏗️ Modern Full-Stack System

- Angular frontend
- FastAPI backend
- Qdrant vector database
- Redis infrastructure
- Docker Compose deployment
- Modular AI architecture

---

## 🧠 RAG Pipeline Architecture

Assessly uses a production-oriented Retrieval-Augmented Generation pipeline designed for large enterprise-style documents.

### ⚙️ Core Components

#### 📄 Document Parsing

Assessly uses layout-aware parsing to preserve:

- headings
- sections
- tables
- narrative structure
- contextual hierarchy

Current parsing stack:

- Docling
- PDF structural extraction
- Metadata enrichment

---

#### 🧩 Chunking Strategy

Assessly uses:

- semantic chunking
- section-aware chunking
- parent-child chunk architecture

This helps reduce context fragmentation and improves retrieval quality for long technical documents.

---

#### 🧠 Embeddings

Dense embeddings:

- `bge-m3`

Sparse retrieval:

- BM25 sparse vectors using FastEmbed

Embedding generation is configurable through Ollama-compatible APIs.

---

#### 🗂 Vector Database

Assessly uses Qdrant for:

- dense vector search
- sparse vector search
- hybrid retrieval
- metadata filtering
- parent-child storage architecture

Collections:

- `parent_chunks`
- `child_chunks`

---

#### 🔍 Retrieval Pipeline

```text
User Query
   ↓
Dense Retrieval
   ↓
Sparse Retrieval
   ↓
Hybrid Fusion
   ↓
Parent Context Assembly
   ↓
Prompt Construction
   ↓
LLM Generation
```

Features:

- Hybrid retrieval
- User-filtered retrieval
- Upload-session filtering
- Parent context reconstruction
- Metadata-aware search

---

#### 🤖 LLM Generation

Assessly currently supports Ollama-compatible local models.

Example models:

- `qwen2.5:7b`
- `qwen3:4b`
- `mistral`

The generation pipeline focuses on:

- grounded answers
- context-aware responses
- reduced hallucinations
- enterprise-style retrieval workflows

---

## ⚡ Production-Grade Engineering

One major goal of Assessly is exploring how real RAG systems are engineered beyond simple demo architectures.

### ✅ Implemented

#### Redis Streams Queue Architecture

- Ingestion job queues
- Query job queues
- Consumer groups
- Stale job recovery

#### Background Workers

- Asynchronous ingestion
- Asynchronous query execution
- Isolated worker processes

#### PostgreSQL Metadata Layer

Stores:

- users
- documents
- upload sessions
- ingestion jobs
- refresh tokens
- audit events

#### Multi-User Isolation

Isolation exists across:

- JWT identity
- API authorization
- Redis jobs
- PostgreSQL metadata
- Qdrant retrieval filters

#### SSE Live Streaming

Real-time streaming for:

- ingestion logs
- query progress
- worker status updates

#### Safe Re-Ingestion

Assessly prevents accidental data corruption:

- new vectors are inserted first
- old vectors are removed only after successful ingestion

#### Infrastructure Protection

- upload rate limiting
- query rate limiting
- LLM concurrency limiting
- upload size limits

---

## 🏗️ Tech Stack

### Frontend

- Angular 21
- TypeScript
- RxJS

### Backend

- FastAPI
- Python 3.11
- Uvicorn
- Gunicorn
- Pydantic

### AI / RAG Pipeline

- LangChain
- Ollama
- Qdrant
- FastEmbed
- `bge-m3` embeddings

### Infrastructure

- Redis
- Redis Streams
- PostgreSQL
- Docker Compose

### PDF Processing

- Docling
- Pillow
- OpenCV

### Authentication

- JWT access tokens
- Refresh-token cookies
- Passlib/Bcrypt

---

## 📄 Ingestion Flow

```text
PDF Upload
   ↓
Validation & Metadata Creation
   ↓
Redis Ingestion Queue
   ↓
Background Worker
   ↓
Document Parsing
   ↓
Chunk Creation
   ↓
Embedding Generation
   ↓
Qdrant Storage
   ↓
Job Completion + SSE Updates
```

---

## ❓ Query Flow

```text
User Question
   ↓
FastAPI Query API
   ↓
Redis Query Queue
   ↓
Query Worker
   ↓
Hybrid Retrieval
   ↓
Parent Context Assembly
   ↓
LLM Generation
   ↓
Streaming Result Updates
```

---

## 🔐 Authentication Flow

Supported flows:

- User registration
- Login
- JWT authentication
- Refresh tokens
- Guest/demo mode

Guest users:

- can use demo querying
- cannot upload private documents
- cannot delete documents

---

## 📡 API Endpoints

### Authentication

```text
POST /auth/register
POST /auth/login
POST /auth/guest
POST /auth/refresh
POST /auth/logout
GET  /auth/me
```

### Ingestion

```text
POST /ingest
GET  /ingest/jobs/{job_id}
GET  /ingest/stream/{job_id}
```

### Query

```text
POST /query
GET  /query/jobs/{query_job_id}
GET  /query/jobs/{query_job_id}/stream
```

### Knowledge Base

```text
GET    /knowledge-base/files
DELETE /knowledge-base/files/{document_id}
```

### Health

```text
GET /health/redis
GET /health/qdrant
GET /health/postgres
```

---

## 🐳 Docker Setup

### Development Infrastructure

```bash
docker compose up -d redis qdrant postgres worker query_worker
```

### Production-Style Stack

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

### Useful Checks

```bash
docker compose ps
docker compose logs -f worker
docker compose logs -f query_worker
docker compose logs -f redis
docker compose logs -f qdrant
docker compose logs -f postgres
```

---

## 🛠️ Manual Setup

### 1️⃣ Clone Repository

```bash
git clone https://github.com/your-username/assessly.git
cd Assessly
```

### 2️⃣ Backend Setup

```bash
cd backend

python -m venv venv
venv\Scripts\activate

pip install -r requirements.txt

alembic upgrade head

uvicorn app.main:app --reload
```

Backend:

```text
http://localhost:8000
```

### 3️⃣ Frontend Setup

```bash
cd frontend

npm install
npm start
```

Frontend:

```text
http://localhost:4200
```

### 4️⃣ Model Runtime

Assessly expects an Ollama-compatible API configured by `OLLAMA_BASE_URL`.

Example local models:

```bash
ollama pull bge-m3
ollama pull qwen2.5:7b
```

---

## 🧪 How To Use

1. Register or log in
2. Upload a PDF
3. Watch ingestion progress live
4. Ask questions against your knowledge base
5. Receive grounded AI-generated answers
6. View or delete your own knowledge-base files

Guest mode:

- Guest users can use demo/query flows
- Guest users cannot upload or delete private documents

---

## 📊 Production Readiness Status

Assessly has a strong production-grade architecture direction and several production-style foundations already implemented.

### ✅ Implemented Foundations

- Worker-based ingestion
- Worker-based querying
- Redis Streams architecture
- PostgreSQL metadata persistence
- Qdrant hybrid retrieval
- JWT authentication
- Multi-user isolation
- SSE streaming logs
- Docker Compose infrastructure
- Alembic migrations
- Rate limiting
- Upload size limits
- Safe re-ingestion handling
- Health endpoints
- OCR support
- Image and diagram understanding

### 🚧 Still In Progress

- Full automated test coverage
- Advanced monitoring and observability
- Structured centralized logging
- Production migration automation
- Horizontal worker scaling
- Advanced citations and confidence scoring
- Advanced OCR and image-heavy PDF understanding
- Backup and restore strategy
- HTTPS reverse proxy and production secret management
- Load testing for expected concurrent usage

---

## 📁 Repository Structure

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

## 💡 Vision

Assessly aims to explore what production-grade AI knowledge systems should actually look like.

The focus is not only on LLM responses — but also on:

- scalable retrieval architecture
- reliable ingestion systems
- multi-user isolation
- durable metadata
- background worker orchestration
- enterprise-style RAG engineering

The long-term goal is to evolve Assessly into a next-generation AI knowledge platform capable of handling real operational and enterprise documentation workflows.

---

## 👨‍💻 Author

Imran Bahelim  
Lead Fullstack + AI Engineer

---

## ⭐ Support

If you like this project, consider giving it a ⭐ on GitHub.
