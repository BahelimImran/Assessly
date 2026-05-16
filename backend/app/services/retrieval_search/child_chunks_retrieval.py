# from app.db.chroma_client import collection
from app.db.qdrant_client import qdrant
from qdrant_client.models import Filter, FieldCondition, MatchValue
from qdrant_client.models import (
    Filter,
    Prefetch,
    FusionQuery,
    Fusion,
    SparseVector,
)
from app.core.config import *
from typing import List, Dict, Any
import numpy as np
from app.services.model_client import post_json_with_retry



def get_sparse_embedding(text: str):
    from app.db.qdrant_client import get_sparse_model

    return list(get_sparse_model().embed([text]))[0]

def get_embedding(text: str) -> List[float]:
    data = post_json_with_retry(
        f"{OLLAMA_BASE_URL}/api/embeddings",
        {"model": EMBED_MODEL, "prompt": text},
        timeout=EMBED_REQUEST_TIMEOUT_SECONDS,
        request_name="ollama_query_embedding"
    )
    embedding = data.get("embedding") or data.get("embeddings", [[]])[0]

    if not embedding:
        raise RuntimeError("Embedding generation failed. Empty embedding returned.")
    
    return embedding


def build_qdrant_filter(where_filter: dict | None = None) -> Filter | None:
    """
    Convert a flat payload filter into a Qdrant filter.
    Example:
    {"document_id": "abc"} 
    becomes Qdrant FieldCondition.
    """

    if not where_filter:
        return None

    must_conditions = []

    for key, value in where_filter.items():
        if value in [None, ""]:
            continue

        must_conditions.append(
            FieldCondition(
                key=key,
                match=MatchValue(value=value)
            )
        )

    if not must_conditions:
        return None

    return Filter(must=must_conditions)

def hybrid_search_child_chunks(
    query: str,
    top_k: int = 10,
    where_filter: Filter | None = None,
    prefetch_limit: int = 20
    
) -> List[Dict[str, Any]]:

    qdrant_filter = build_qdrant_filter(where_filter)

    dense_query = get_embedding(query)

    sparse_query = get_sparse_embedding(query)

    sparse_vector = SparseVector(
        indices=sparse_query.indices.tolist(),
        values=sparse_query.values.tolist(),
    )

    print("CHILD_COLLECTION:", CHILD_COLLECTION)
    print("top_k:", top_k)
    print("prefetch_limit:", prefetch_limit)
    print("qdrant_filter:", qdrant_filter)
    print("dense_query len:", len(dense_query))
    print("sparse indices:", len(sparse_vector.indices))
    print("sparse values:", len(sparse_vector.values))

    info = qdrant.get_collection(CHILD_COLLECTION)
    print("collection info:", info)

    count = qdrant.count(
        collection_name=CHILD_COLLECTION,
        exact=True
    )
    print("child count:", count.count)

    response = qdrant.query_points(
        collection_name=CHILD_COLLECTION,

        prefetch=[
            Prefetch(
                query=dense_query,
                using="dense",
                limit=prefetch_limit,
                filter=qdrant_filter,
            ),
            Prefetch(
                query=sparse_vector,
                using="sparse",
                limit=prefetch_limit,
                filter=qdrant_filter,
            ),
        ],

        query=FusionQuery(
            fusion=Fusion.RRF
        ),

        limit=top_k,
        with_payload=True,
        with_vectors=False,
    )

    results = []

    for point in response.points:
        payload = point.payload or {}

        results.append({
            "id": point.id,
            "score": point.score,
            "text": payload.get("chunk_text", ""),
            "parent_id": payload.get("parent_id"),
            "payload": payload,
            "retrieval_type": "hybrid_rrf",
        })

    return results

def extract_unique_parent_ids(child_results: list[dict]) -> list[str]:
    parent_ids = []

    for result in child_results:
        parent_id = result.get("parent_id")

        if parent_id and parent_id not in parent_ids:
            parent_ids.append(parent_id)

    parent_ids = rank_parent_ids_from_children(
        child_results=child_results,
        max_parents=2
    )
    return parent_ids

def rank_parent_ids_from_children(child_results: list[dict], max_parents: int = 3) -> list[str]:
    parent_scores = {}

    for rank, result in enumerate(child_results, start=1):
        parent_id = result.get("parent_id")
        if not parent_id:
            continue

        score = float(result.get("score") or 0)

        if parent_id not in parent_scores:
            parent_scores[parent_id] = {
                "best_score": score,
                "hit_count": 0,
                "best_rank": rank,
            }

        parent_scores[parent_id]["hit_count"] += 1
        parent_scores[parent_id]["best_score"] = max(
            parent_scores[parent_id]["best_score"],
            score
        )
        parent_scores[parent_id]["best_rank"] = min(
            parent_scores[parent_id]["best_rank"],
            rank
        )

    ranked = sorted(
        parent_scores.items(),
        key=lambda x: (
            x[1]["best_score"],
            x[1]["hit_count"],
            -x[1]["best_rank"],
        ),
        reverse=True
    )

    return [parent_id for parent_id, _ in ranked[:max_parents]]
# def get_parent_chunks_from_hybrid_search(
#     query: str,
#     top_k: int = 10,
#     where_filter: dict | None = None
    
# ) -> list[dict]:

#     qdrant_filter = build_qdrant_filter(where_filter)

#     child_results = hybrid_search_child_chunks(
#         query=query,
#         top_k=top_k,
#         prefetch_limit=top_k * 2,
#         qdrant_filter=qdrant_filter
#     )

#     parent_ids = extract_unique_parent_ids(child_results)

#     # parent_chunks = fetch_parent_chunks(parent_ids)

#     return parent_ids
