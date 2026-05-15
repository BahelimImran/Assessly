import os
from dotenv import load_dotenv

load_dotenv()

# OLLAMA_BASE_URL = "http://localhost:11434"

# LLM_MODEL = "mistral"
# EMBED_MODEL = "nomic-embed-text"

# CHROMA_COLLECTION = "assessly_docs"
# PERSIST_DIR = "./chromadb"

MAX_UPLOAD_SIZE_MB = 25
MAX_UPLOAD_SIZE_BYTES = MAX_UPLOAD_SIZE_MB * 1024 * 1024
MAX_PDF_PAGES = 100
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")

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

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))

FRONTEND_URL = os.getenv(
    "FRONTEND_URL",
    "http://localhost:4200"
)

API_DOMAIN = os.getenv("API_DOMAIN", "http://localhost:8000")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
VLLM_BASE_URL = os.getenv("VLLM_BASE_URL", "")
EMBED_PROVIDER = os.getenv("EMBED_PROVIDER", "ollama")
EMBED_MODEL = os.getenv("EMBED_MODEL", "bge-m3")
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama")
LLM_MODEL = os.getenv("LLM_MODEL", "qwen2.5:7b")
RERANKER_MODEL = os.getenv("RERANKER_MODEL", "BAAI/bge-reranker-v2-m3")
VISION_MODEL = os.getenv("VISION_MODEL", "qwen2.5vl:3b")
VECTOR_DB = os.getenv("VECTOR_DB", "qdrant")
OCR_ENGINE = os.getenv("OCR_ENGINE", "paddleocr")
LAYOUT_PARSER = os.getenv("LAYOUT_PARSER", "docling")
