import os

# OLLAMA_BASE_URL = "http://localhost:11434"

# LLM_MODEL = "mistral"
# EMBED_MODEL = "nomic-embed-text"

# CHROMA_COLLECTION = "assessly_docs"
# PERSIST_DIR = "./chromadb"

QDRANT_COLLECTION = "assessly_qdrant_docs"
PARENT_COLLECTION = "parent_chunks"

CHILD_COLLECTION = "child_chunks"
VECTOR_SIZE = 1024  # bge-m3 = 1024

PERSIST_DIR = "./qdrant_db"

TOP_K = 5

os.environ["ANONYMIZED_TELEMETRY"] = "False"
# os.environ["CHROMA_TELEMETRY"] = "FALSE"