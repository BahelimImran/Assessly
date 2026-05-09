from typing import List, Dict, Any
import re
import hashlib

def normalize_text(text: str) -> str:
    text = text or ""
    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def content_hash(text: str)-> str:
    return hashlib.sha256(normalize_text(text).encode("utf-8")).hexdigest

def get_dedupe_key(item: Dict[str, Any])->str:
    metadata = item.get("metadata", {}) or {}

    # Best: stable chunk id created during ingestion
    if metadata.get("chunk_id"):
        return f"chunk_id:{metadata['chunk_id']}"

    # Good: stored chunk hash
    if metadata.get("chunk_hash"):
        return f"chunk_hash:{metadata['chunk_hash']}"

    # Fallback: hash actual content
    return f"content_hash:{content_hash(item.get('content', ''))}"


def reciprocal_rank_fusion(
    vector_results: List[Dict[str, Any]],
    bm25_results: List[Dict[str, Any]],
    k: int = 60,
    max_candidates: int = 30,
) -> List[Dict[str, Any]]:
    """
    Merge vector and BM25 results using Reciprocal Rank Fusion.
    Does not mutate original vector/BM25 result objects.
    """
    fused: Dict[str, Dict[str, Any]] = {}

    def add_result(item: Dict[str, Any], rank: int, source: str):
        dedupe_key = get_dedupe_key(item)
        original_id = item["id"]

        if dedupe_key not in fused:
            fused[dedupe_key] = {
                "id": original_id,
                "dedupe_key": dedupe_key,
                "content": item.get("content", ""),
                "metadata": item.get("metadata", {}),
                "vector_score": 0.0,
                "vector_distance": None,
                "bm25_score": 0.0,
                "rrf_score": 0.0,
                "sources": [],
                "merged_ids":[]
            }

        fused_item = fused[dedupe_key]
        fused_item["rrf_score"] += 1 / (k + rank)

        if original_id and original_id not in fused_item["merged_ids"]:
            fused_item["merged_ids"].append(original_id)

        if source == "vector":
            fused_item["vector_score"] = max(
                fused_item.get("vector_score", 0.0),
                item.get("vector_score", 0.0)
            )
            fused_item["vector_distance"] = item.get("vector_distance")

        elif source == "bm25":
            fused_item["bm25_score"] = max(
                fused_item.get("bm25_score", 0.0),
                item.get("bm25_score", 0.0)
            )

        if source not in fused_item["sources"]:
            fused_item["sources"].append(source)

    for rank, item in enumerate(vector_results, start=1):
        add_result(item, rank, "vector")

    for rank, item in enumerate(bm25_results, start=1):
        add_result(item, rank, "bm25")

    return sorted(
        fused.values(),
        key=lambda x: x.get("rrf_score", 0.0),
        reverse=True,
    )[:max_candidates]
