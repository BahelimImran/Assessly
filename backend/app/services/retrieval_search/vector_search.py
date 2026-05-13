# # from app.db.chroma_client import collection
# from app.db.qdrant_client import qdrant
# from qdrant_client.models import Filter, FieldCondition, MatchValue
# from qdrant_client.models import (
#     Filter,
#     Prefetch,
#     FusionQuery,
#     Fusion,
#     SparseVector,
# )
# from app.core.config import *
# import requests
# from typing import List, Dict, Any
# import numpy as np
# from dotenv import load_dotenv; load_dotenv()
# import os; 
# EMBED_PROVIDER = os.getenv("EMBED_PROVIDER")
# EMBED_MODEL = os.getenv("EMBED_MODEL")
# LLM_PROVIDER = os.getenv("LLM_PROVIDER")
# LLM_MODEL = os.getenv("LLM_MODEL")
# OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL")


# from fastembed import SparseTextEmbedding

# sparse_model = SparseTextEmbedding(
#     model_name="Qdrant/bm25"
# )


# def get_sparse_embedding(text: str):
#     return list(sparse_model.embed([text]))[0]

# def get_embedding(text: str) -> List[float]:
#     response = requests.post(
#         f"{OLLAMA_BASE_URL}/api/embeddings",
#         json={"model": EMBED_MODEL, "prompt": text},
#         timeout=120
#     )
#     response.raise_for_status() 
#     data = response.json()
#     embedding = data.get("embedding") or data.get("embeddings", [[]])[0]

#     if not embedding:
#         raise RuntimeError("Embedding generation failed. Empty embedding returned.")
    
#     return embedding

# # def cosine_similarity(emb1: List[float], emb2: List[float]) -> float:
    
# #     a = np.array(emb1)
# #     b = np.array(emb2)
# #     return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

# def _distance_to_similarity(distance: float | None) -> float:
#     """
#     Chroma returns distance. For cosine space, lower is better.
#     This converts it into an easy-to-read similarity-like score.
#     """
#     if distance is None:
#         return 0.0
#     return 1 / (1 + float(distance))


# # def vector_search(query: str, top_k: int = 20, where_filter: dict | None = None) -> List[Dict[str, Any]]:
   
# #     query_embedding = get_embedding(query)

# #     # results = qdrant.query(
# #     #     query_embeddings=[query_embedding],
# #     #     n_results=top_k,
# #     #     include=["documents", "metadatas", "distances"],
# #     # )
# #     query_args = {
# #     "query_embeddings": [query_embedding],
# #     "n_results": top_k,
# #     "include": ["documents", "metadatas", "distances"],
# #     }

# #     if where_filter:
# #         query_args["where"] = where_filter
    
# #     results = qdrant.query(**query_args) #Todo

# #     ids = results.get("ids", [[]])[0]
# #     docs = results.get("documents", [[]])[0]
# #     metas = results.get("metadatas", [[]])[0]
# #     distances = results.get("distances", [[]])[0]

# #     response = []
# #     for doc_id, doc, meta, distance in zip(ids, docs, metas, distances):
# #         response.append({
# #             "id": doc_id,
# #             "content": doc,
# #             "metadata": meta or {},
# #             "vector_distance": float(distance),
# #             "vector_score": _distance_to_similarity(distance),
# #             "retrieval_source": "vector",
# #         })

# #     return response

# def build_qdrant_filter(where_filter: dict | None = None) -> Filter | None:
#     """
#     Convert simple Chroma-style filter into Qdrant filter.
#     Example:
#     {"document_id": "abc"} 
#     becomes Qdrant FieldCondition.
#     """

#     if not where_filter:
#         return None

#     must_conditions = []

#     for key, value in where_filter.items():
#         must_conditions.append(
#             FieldCondition(
#                 key=key,
#                 match=MatchValue(value=value)
#             )
#         )

#     return Filter(must=must_conditions)

# def hybrid_search_child_chunks(
#     query: str,
#     top_k: int = 10,
#     where_filter: Filter | None = None,
#     prefetch_limit: int = 20
    
# ) -> List[Dict[str, Any]]:

#     qdrant_filter = build_qdrant_filter(where_filter)

#     dense_query = get_embedding(query)

#     sparse_query = get_sparse_embedding(query)

#     sparse_vector = SparseVector(
#         indices=sparse_query.indices.tolist(),
#         values=sparse_query.values.tolist(),
#     )

#     print("CHILD_COLLECTION:", CHILD_COLLECTION)
#     print("top_k:", top_k)
#     print("prefetch_limit:", prefetch_limit)
#     print("qdrant_filter:", qdrant_filter)
#     print("dense_query len:", len(dense_query))
#     print("sparse indices:", len(sparse_vector.indices))
#     print("sparse values:", len(sparse_vector.values))

#     info = qdrant.get_collection(CHILD_COLLECTION)
#     print("collection info:", info)

#     count = qdrant.count(
#         collection_name=CHILD_COLLECTION,
#         exact=True
#     )
#     print("child count:", count.count)

#     response = qdrant.query_points(
#         collection_name=CHILD_COLLECTION,

#         prefetch=[
#             Prefetch(
#                 query=dense_query,
#                 using="dense",
#                 limit=prefetch_limit,
#                 # filter=qdrant_filter,
#             ),
#             Prefetch(
#                 query=sparse_vector,
#                 using="sparse",
#                 limit=prefetch_limit,
#                 # filter=qdrant_filter,
#             ),
#         ],

#         query=FusionQuery(
#             fusion=Fusion.RRF
#         ),

#         limit=top_k,
#         with_payload=True,
#         with_vectors=False,
#     )

#     results = []

#     for point in response.points:
#         payload = point.payload or {}

#         results.append({
#             "id": point.id,
#             "score": point.score,
#             "text": payload.get("chunk_text", ""),
#             "parent_id": payload.get("parent_id"),
#             "payload": payload,
#             "retrieval_type": "hybrid_rrf",
#         })

#     return results

# def vector_search(
#     query: str,
#     top_k: int = 20,
#     where_filter: dict | None = None
# ) -> List[Dict[str, Any]]:

#     # child_filter = {
#     #     **(where_filter or {}),
#     #     "content_type": "child_chunk"
#     # }
    
    

#     qdrant_filter = build_qdrant_filter(where_filter)
#     results = hybrid_search_child_chunks(
#         query,
#         qdrant_filter,
#     )

#     # query_embedding = get_embedding(query)

#     # response = qdrant.query_points(
#     #     collection_name=CHILD_COLLECTION,
#     #     # query_vector=query_embedding,
#     #     query=query_embedding,
#     #     using="dense",
#     #     query_filter=qdrant_filter,
#     #     limit=top_k,
#     #     with_payload=True,
#     #     with_vectors=False
#     # )

#     # results = []

#     # for point in response.points:
#     #     payload = point.payload or {}

#     #     results.append({
#     #         # "id": str(point.id),
#     #         # "content": payload.get("content", ""),
#     #         # "metadata": payload,
#     #         # "vector_distance": 1 - float(hit.score),
#     #         # "vector_score": float(point.score),
#     #         # "retrieval_source": "vector",

#     #         "id": point.id,
#     #         "score": point.score,
#     #         "text": payload.get("text", ""),
#     #         "parent_id": payload.get("parent_id"),
#     #         "payload": payload,
#     #         "retrieval_type": "dense"            
#     #     })

#     return results

