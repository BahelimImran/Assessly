from app.core.config import PERSIST_DIR, QDRANT_COLLECTION, VECTOR_SIZE
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams


qdrant = QdrantClient(path=PERSIST_DIR)

collection = qdrant.get_collections().collections
# existing = [c.name for c in collections]

if not qdrant.collection_exists(QDRANT_COLLECTION):
    qdrant.create_collection(
        collection_name = QDRANT_COLLECTION,
        vectors_config=VectorParams(
            size=VECTOR_SIZE, #embedding dimention
            distance = Distance.COSINE
        )
    )