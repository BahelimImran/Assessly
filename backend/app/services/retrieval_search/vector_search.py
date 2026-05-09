# from app.db.chroma_client import collection
from app.db.qdrant_client import qdrant
from qdrant_client.models import Filter, FieldCondition, MatchValue
from app.core.config import *
import requests
from typing import List, Dict, Any
import numpy as np
from dotenv import load_dotenv; load_dotenv()
import os; 
EMBED_PROVIDER = os.getenv("EMBED_PROVIDER")
EMBED_MODEL = os.getenv("EMBED_MODEL")
LLM_PROVIDER = os.getenv("LLM_PROVIDER")
LLM_MODEL = os.getenv("LLM_MODEL")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL")


def get_embedding(text: str) -> List[float]:
    response = requests.post(
        f"{OLLAMA_BASE_URL}/api/embeddings",
        json={"model": EMBED_MODEL, "prompt": text},
        timeout=120
    )
    response.raise_for_status() 
    data = response.json()
    embedding = data.get("embedding") or data.get("embeddings", [[]])[0]

    if not embedding:
        raise RuntimeError("Embedding generation failed. Empty embedding returned.")
    
    return embedding

# def cosine_similarity(emb1: List[float], emb2: List[float]) -> float:
    
#     a = np.array(emb1)
#     b = np.array(emb2)
#     return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

def _distance_to_similarity(distance: float | None) -> float:
    """
    Chroma returns distance. For cosine space, lower is better.
    This converts it into an easy-to-read similarity-like score.
    """
    if distance is None:
        return 0.0
    return 1 / (1 + float(distance))


# def vector_search(query: str, top_k: int = 20, where_filter: dict | None = None) -> List[Dict[str, Any]]:
   
#     query_embedding = get_embedding(query)

#     # results = qdrant.query(
#     #     query_embeddings=[query_embedding],
#     #     n_results=top_k,
#     #     include=["documents", "metadatas", "distances"],
#     # )
#     query_args = {
#     "query_embeddings": [query_embedding],
#     "n_results": top_k,
#     "include": ["documents", "metadatas", "distances"],
#     }

#     if where_filter:
#         query_args["where"] = where_filter
    
#     results = qdrant.query(**query_args) #Todo

#     ids = results.get("ids", [[]])[0]
#     docs = results.get("documents", [[]])[0]
#     metas = results.get("metadatas", [[]])[0]
#     distances = results.get("distances", [[]])[0]

#     response = []
#     for doc_id, doc, meta, distance in zip(ids, docs, metas, distances):
#         response.append({
#             "id": doc_id,
#             "content": doc,
#             "metadata": meta or {},
#             "vector_distance": float(distance),
#             "vector_score": _distance_to_similarity(distance),
#             "retrieval_source": "vector",
#         })

#     return response

def build_qdrant_filter(where_filter: dict | None = None) -> Filter | None:
    """
    Convert simple Chroma-style filter into Qdrant filter.
    Example:
    {"document_id": "abc"} 
    becomes Qdrant FieldCondition.
    """

    if not where_filter:
        return None

    must_conditions = []

    for key, value in where_filter.items():
        must_conditions.append(
            FieldCondition(
                key=key,
                match=MatchValue(value=value)
            )
        )

    return Filter(must=must_conditions)


def vector_search(
    query: str,
    top_k: int = 20,
    where_filter: dict | None = None
) -> List[Dict[str, Any]]:

    query_embedding = get_embedding(query)

    qdrant_filter = build_qdrant_filter(where_filter)

    results = qdrant.search(
        collection_name=QDRANT_COLLECTION,
        query_vector=query_embedding,
        query_filter=qdrant_filter,
        limit=top_k,
        with_payload=True,
        with_vectors=False
    )

    response = []

    for hit in results:
        payload = hit.payload or {}

        response.append({
            "id": str(hit.id),
            "content": payload.get("content", ""),
            "metadata": payload,
            "vector_distance": 1 - float(hit.score),
            "vector_score": float(hit.score),
            "retrieval_source": "vector",
        })

    return response