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

from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor

from app.core.tracing import setup_tracing
from opentelemetry.trace import get_current_span

from app.core.langfuse import get_langfuse, get_trace_context

logger = logging.getLogger("assessly.api")

setup_tracing()  # must run before FastAPIInstrumentor.instrument_app / before redis is imported elsewhere

app = FastAPI(
    title="Assessly AI",
    version="1.0.0"
)

FastAPIInstrumentor.instrument_app(app)   # auto-traces every route
RedisInstrumentor().instrument()          # auto-traces every redis_client call (hset, xadd, etc.)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


@app.middleware("http")
async def latency_logging_middleware(request: Request, call_next):
    start = time.perf_counter()

    langfuse = get_langfuse()
    trace_ctx = get_trace_context()

    lf_trace = langfuse.trace(
        name="api_request",
        input={
            "method": request.method,
            "path": request.url.path,
        },
        metadata={
            "otel_trace_id": trace_ctx["trace_id"]
        }
    )

    try:
        response = await call_next(request)

        duration_ms = round((time.perf_counter() - start) * 1000, 2)

        span = get_current_span()
        ctx = span.get_span_context()
        trace_id = format(ctx.trace_id, "032x") if ctx.trace_id else "unknown"

        logger.info(json.dumps({
            "event": "api_request",
            "trace_id": trace_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
        }))

        response.headers["x-trace-id"] = trace_id

        lf_trace.update(
            output={"status_code": response.status_code},
            metadata={"duration_ms": duration_ms}
        )

        return response

    except Exception as e:
        lf_trace.update(
            level="ERROR",
            status_message=str(e)
        )
        raise

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
