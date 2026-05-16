from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import ingest, query
from app.api.knowledge_base import router as knowledge_base_router
from app.core.config import FRONTEND_URL
from app.db.postgres import init_db

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

# Register routers
app.include_router(ingest.router, prefix="/ingest", tags=["Ingest"])
app.include_router(query.router, prefix="/query", tags=["Query"])
app.include_router(knowledge_base_router,
    prefix="/knowledge-base",
    tags=["Knowledge Base"]
)

@app.on_event("startup")
# That creates missing Postgres metadata tables during development.

# Why: This prevents errors if tables do not exist yet.
def startup():
    init_db()

@app.get("/")
def root():
    return {"status": "RAG API running"}
