import os
from dotenv import load_dotenv

load_dotenv()

# OLLAMA_BASE_URL = "http://localhost:11434"

# LLM_MODEL = "mistral"
# EMBED_MODEL = "nomic-embed-text"

# CHROMA_COLLECTION = "assessly_docs"
# PERSIST_DIR = "./chromadb"

MAX_UPLOAD_SIZE_MB = int(os.getenv("MAX_UPLOAD_SIZE_MB", "25"))
MAX_UPLOAD_SIZE_BYTES = MAX_UPLOAD_SIZE_MB * 1024 * 1024
MAX_PDF_PAGES = 100
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")
JOB_TTL_SECONDS = int(os.getenv("JOB_TTL_SECONDS", "86400"))
MAX_ACTIVE_JOBS_PER_USER = int(os.getenv("MAX_ACTIVE_JOBS_PER_USER", "0"))  # For production/staging, set: MAX_ACTIVE_JOBS_PER_USER=3
JOB_STREAM_RECLAIM_IDLE_MS = int(os.getenv("JOB_STREAM_RECLAIM_IDLE_MS", "3600000"))
JOB_STREAM_BLOCK_MS = int(os.getenv("JOB_STREAM_BLOCK_MS", "5000"))
AUTO_CREATE_DB_TABLES = os.getenv("AUTO_CREATE_DB_TABLES", "true").lower() == "true"

QUERY_RATE_LIMIT_PER_MINUTE = int(os.getenv("QUERY_RATE_LIMIT_PER_MINUTE", "0"))
UPLOAD_RATE_LIMIT_PER_MINUTE = int(os.getenv("UPLOAD_RATE_LIMIT_PER_MINUTE", "0"))
RATE_LIMIT_WINDOW_SECONDS = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))
GUEST_QUERY_RATE_LIMIT_PER_MINUTE = int(os.getenv("GUEST_QUERY_RATE_LIMIT_PER_MINUTE", "5"))
LLM_CONCURRENCY_LIMIT = int(os.getenv("LLM_CONCURRENCY_LIMIT", "0"))
LLM_CONCURRENCY_TTL_SECONDS = int(os.getenv("LLM_CONCURRENCY_TTL_SECONDS", "900"))
QUERY_JOB_TTL_SECONDS = int(os.getenv("QUERY_JOB_TTL_SECONDS", "86400"))
QUERY_STREAM_RECLAIM_IDLE_MS = int(os.getenv("QUERY_STREAM_RECLAIM_IDLE_MS", "3600000"))
QUERY_STREAM_BLOCK_MS = int(os.getenv("QUERY_STREAM_BLOCK_MS", "5000"))
STREAM_TOKEN_TTL_SECONDS = int(os.getenv("STREAM_TOKEN_TTL_SECONDS", "120"))

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

POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
POSTGRES_DB = os.getenv("POSTGRES_DB", "assessly")
POSTGRES_USER = os.getenv("POSTGRES_USER", "assessly")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "assessly")
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"postgresql+psycopg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
)

FRONTEND_URL = os.getenv(
    "FRONTEND_URL",
    "http://localhost:4200"
)

API_DOMAIN = os.getenv("API_DOMAIN", "http://localhost:8000")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-only-change-me")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
REFRESH_COOKIE_NAME = os.getenv("REFRESH_COOKIE_NAME", "assessly_refresh_token")
REFRESH_COOKIE_SECURE = os.getenv("REFRESH_COOKIE_SECURE", "false").lower() == "true"
REFRESH_COOKIE_SAMESITE = os.getenv("REFRESH_COOKIE_SAMESITE", "lax")
DEMO_USER_ID = os.getenv("DEMO_USER_ID", "demo_user")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
VLLM_BASE_URL = os.getenv("VLLM_BASE_URL", "")
EMBED_PROVIDER = os.getenv("EMBED_PROVIDER", "ollama")
EMBED_MODEL = os.getenv("EMBED_MODEL", "bge-m3")
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama")
LLM_MODEL = os.getenv("LLM_MODEL", "qwen2.5:7b")
QUERY_ROUTER_LLM_MODEL = os.getenv("QUERY_ROUTER_LLM_MODEL", "llama3.2:3b")
ANSWER_VERIFICATION_LLM_MODEL = os.getenv("ANSWER_VERIFICATION_LLM_MODEL", "gemma3:4b")
MAX_RETRIES = os.getenv("MAX_RETRIES", "2")
RERANKER_MODEL = os.getenv("RERANKER_MODEL", "BAAI/bge-reranker-v2-m3")
VISION_MODEL = os.getenv("VISION_MODEL", "qwen2.5vl:3b")
VECTOR_DB = os.getenv("VECTOR_DB", "qdrant")
OCR_ENGINE = os.getenv("OCR_ENGINE", "paddleocr")
LAYOUT_PARSER = os.getenv("LAYOUT_PARSER", "docling")

MODEL_REQUEST_RETRIES = int(os.getenv("MODEL_REQUEST_RETRIES", "2"))
MODEL_REQUEST_BACKOFF_SECONDS = float(os.getenv("MODEL_REQUEST_BACKOFF_SECONDS", "1.0"))
EMBED_REQUEST_TIMEOUT_SECONDS = int(os.getenv("EMBED_REQUEST_TIMEOUT_SECONDS", "120"))
EMBED_BATCH_REQUEST_TIMEOUT_SECONDS = int(os.getenv("EMBED_BATCH_REQUEST_TIMEOUT_SECONDS", "300"))
LLM_REQUEST_TIMEOUT_SECONDS = int(os.getenv("LLM_REQUEST_TIMEOUT_SECONDS", "300"))
VISION_REQUEST_TIMEOUT_SECONDS = int(os.getenv("VISION_REQUEST_TIMEOUT_SECONDS", "180"))
