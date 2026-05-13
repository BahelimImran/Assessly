# from typing import List, Dict, Any
# import re

# from rank_bm25 import BM25Okapi
# from qdrant_client.models import Filter, FieldCondition, MatchValue

# from app.db.qdrant_client import qdrant
# from app.core.config import QDRANT_COLLECTION


# def tokenize(text: str) -> List[str]:
#     return re.findall(r"\b\w+\b", (text or "").lower())


# def build_qdrant_filter(where_filter: dict | None = None) -> Filter | None:

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


# def bm25_search(
#     query: str,
#     top_k: int = 20,
#     where_filter: dict | None = None
# ) -> List[Dict[str, Any]]:

#     child_filter = {
#         **(where_filter or {}),
#         "content_type": "child_chunk"
#     }
#     qdrant_filter = build_qdrant_filter(child_filter)

#     # Fetch points from Qdrant
#     points, _ = qdrant.scroll(
#         collection_name=QDRANT_COLLECTION,
#         scroll_filter=qdrant_filter,
#         limit=20, # Maximum records to fetch.
#         with_payload=True, # Return metadata + content.
#         with_vectors=False
#     )

#     if not points:
#         return []

#     docs = []
#     metas = []
#     ids = []

#     for point in points:

#         payload = point.payload or {}

#         docs.append(payload.get("content", ""))
#         metas.append(payload)
#         ids.append(str(point.id))

#     if not docs:
#         return []

#     tokenized_docs = [tokenize(doc) for doc in docs]

#     bm25 = BM25Okapi(tokenized_docs)

#     query_tokens = tokenize(query)

#     if not query_tokens:
#         return []

#     scores = bm25.get_scores(query_tokens)

#     ranked = sorted(
#         zip(ids, docs, metas, scores),
#         key=lambda x: x[3],
#         reverse=True,
#     )[:top_k]

#     return [
#         {
#             "id": doc_id,
#             "content": doc,
#             "metadata": meta or {},
#             "bm25_score": float(score),
#             "retrieval_source": "bm25",
#         }
#         for doc_id, doc, meta, score in ranked
#         if float(score) > 0
#     ]