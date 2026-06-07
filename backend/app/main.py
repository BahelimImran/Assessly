import json
import logging
import time
import uuid

from fastapi import FastAPI
from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware

from app.api import admin, auth, health, ingest, query
from app.api.knowledge_base import router as knowledge_base_router
from app.core.config import AUTO_CREATE_DB_TABLES, FRONTEND_URL
from app.db.postgres import init_db

logger = logging.getLogger("assessly.api")

app = FastAPI(
    title="Assessly AI",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


@app.middleware("http")
async def latency_logging_middleware(request: Request, call_next):
    trace_id = request.headers.get("x-trace-id", str(uuid.uuid4()))
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = round((time.perf_counter() - start) * 1000, 2)
    logger.info(
        json.dumps({
            "event": "api_request",
            "trace_id": trace_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
        })
    )
    response.headers["x-trace-id"] = trace_id
    return response

# Register routers
app.include_router(ingest.router, prefix="/ingest", tags=["Ingest"])
app.include_router(query.router, prefix="/query", tags=["Query"])
app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(admin.router, prefix="/admin", tags=["Admin"])
app.include_router(health.router, prefix="/health", tags=["Health"])
app.include_router(knowledge_base_router,
    prefix="/knowledge-base",
    tags=["Knowledge Base"]
)

@app.on_event("startup")
# That creates missing Postgres metadata tables during development.

# Why: This prevents errors if tables do not exist yet.
def startup():
    if AUTO_CREATE_DB_TABLES:
        init_db()

@app.get("/")
def root():
    return {"status": "RAG API running"}
