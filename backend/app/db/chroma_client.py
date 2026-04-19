import chromadb
from app.core.config import PERSIST_DIR, CHROMA_COLLECTION

chroma_client = chromadb.PersistentClient(path=PERSIST_DIR)

collection = chroma_client.get_or_create_collection(
    name=CHROMA_COLLECTION
)