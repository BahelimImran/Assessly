import os

# OLLAMA_BASE_URL = "http://localhost:11434"

# LLM_MODEL = "mistral"
# EMBED_MODEL = "nomic-embed-text"

# CHROMA_COLLECTION = "assessly_docs"
# PERSIST_DIR = "./chromadb"

MAX_UPLOAD_SIZE_MB = 25
MAX_UPLOAD_SIZE_BYTES = MAX_UPLOAD_SIZE_MB * 1024 * 1024
MAX_PDF_PAGES = 100
UPLOAD_DIR = "uploads"

# QDRANT_COLLECTION = "assessly_qdrant_docs"
PARENT_COLLECTION = "parent_chunks"

CHILD_COLLECTION = "child_chunks"
VECTOR_SIZE = 1024  # bge-m3 = 1024

PERSIST_DIR = "./qdrant_db"

TOP_K = 5

os.environ["ANONYMIZED_TELEMETRY"] = "False"
# os.environ["CHROMA_TELEMETRY"] = "FALSE"

# REDIS - Job manager and SSE
QDRANT_URL = os.getenv(
    "QDRANT_URL",
    "http://localhost:6333"
)

QDRANT_COLLECTION = os.getenv(
    "QDRANT_COLLECTION",
    "assessly"
)

REDIS_URL = os.getenv(
    "REDIS_URL",
    "redis://localhost:6379/0"
)

FRONTEND_URL = os.getenv(
    "FRONTEND_URL",
    "http://localhost:4200"
)