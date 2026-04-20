import os

OLLAMA_BASE_URL = "http://localhost:11434"

LLM_MODEL = "mistral"
EMBED_MODEL = "nomic-embed-text"

CHROMA_COLLECTION = "assessly_docs"
PERSIST_DIR = "./chromadb"

TOP_K = 5

os.environ["ANONYMIZED_TELEMETRY"] = "False"
os.environ["CHROMA_TELEMETRY"] = "FALSE"