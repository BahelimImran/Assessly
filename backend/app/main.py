from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import ingest, query
from app.api.knowledge_base import router as knowledge_base_router

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],
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

@app.get("/")
def root():
    return {"status": "RAG API running"}