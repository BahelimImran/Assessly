from app.core.config import PARENT_COLLECTION, CHILD_COLLECTION, QDRANT_URL
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, SparseVectorParams, PointStruct, Filter, FieldCondition, MatchValue
from typing import List, Dict, Any
import uuid
from fastembed import SparseTextEmbedding

sparse_model = SparseTextEmbedding(model_name="Qdrant/bm25") #Todo - For production - prithivida/Splade_PP_en_v1

qdrant = QdrantClient(url=QDRANT_URL)

def create_collections():
    existing = [c.name for c in qdrant.get_collections().collections]

    # Child collection: vector search enabled
    if CHILD_COLLECTION not in existing:
        qdrant.create_collection(
            collection_name=CHILD_COLLECTION,
                vectors_config={
                    "dense": VectorParams(size=1024, distance=Distance.COSINE)
                },
                sparse_vectors_config={
                    "sparse": SparseVectorParams()
                }
            )

    # Parent collection: payload-only collection
    if PARENT_COLLECTION not in existing:
        qdrant.create_collection(
            collection_name=PARENT_COLLECTION,
            vectors_config={}  # no vector needed
        )

# collection = qdrant.get_collections().collections
# # existing = [c.name for c in collections]

# if not qdrant.collection_exists(QDRANT_COLLECTION):
#     qdrant.create_collection(
#         collection_name = QDRANT_COLLECTION,
#         vectors_config=VectorParams(
#             size=VECTOR_SIZE, #embedding dimention
#             distance = Distance.COSINE
#         )
#     )

def collection_exists(collection_name: str) -> bool:
    collections = qdrant.get_collections().collections
    return collection_name in [c.name for c in collections]


def build_document_filter(document_id: str) -> Filter:
    return Filter(
        must=[
            FieldCondition(
                key="document_id",
                match=MatchValue(value=document_id)
            )
        ]
    )


def delete_existing_document(document_id: str) -> dict:
    doc_filter = build_document_filter(document_id)

    deleted = {}

    #Todo - if collection exist then only go for delete
    for collection_name in [PARENT_COLLECTION, CHILD_COLLECTION]:

        if not collection_exists(collection_name):
            deleted[collection_name] = 0
            continue

        count_result = qdrant.count(
            collection_name=collection_name,
            count_filter=doc_filter,
            exact=True
        )

        existing_count = count_result.count

        if existing_count > 0:
            qdrant.delete(
                collection_name=collection_name,
                points_selector=doc_filter
            )

        deleted[collection_name] = existing_count

    return deleted

def document_exists(document_id: str) -> bool:
    create_collections()

    doc_filter = build_document_filter(document_id)

    count_result = qdrant.count(
        collection_name=CHILD_COLLECTION,
        count_filter=doc_filter,
        exact=True
    )

    return count_result.count > 0
