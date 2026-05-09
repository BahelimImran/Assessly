from typing import List, Dict, Any

_reranker = None


def get_reranker():
    global _reranker
    if _reranker is None:
        from FlagEmbedding import FlagReranker

        # Todo - Good CPU-friendly default. Upgrade to BAAI/bge-reranker-v2-m3 later if machine handles it.
        _reranker = FlagReranker("BAAI/bge-reranker-v2-m3", use_fp16=False)
    return _reranker


def rerank_results(
    query: str,
    candidates: List[Dict[str, Any]],
    top_k: int = 5,
) -> List[Dict[str, Any]]:
    if not candidates:
        return []

    pairs = [[query, item.get("content", "")] for item in candidates]

    try:
        reranker = get_reranker()
        scores = reranker.compute_score(pairs)
        if not isinstance(scores, list):
            scores = [scores]
    except Exception as exc:
        # Safe fallback: do not break Q&A if reranker model is not downloaded or fails on laptop.
        print(f"⚠️ Reranker unavailable. Falling back to RRF order. Reason: {exc}")
        return candidates[:top_k]

    reranked = []
    for item, score in zip(candidates, scores):
        copied = dict(item)
        copied["rerank_score"] = float(score)
        reranked.append(copied)

    return sorted(reranked, key=lambda x: x.get("rerank_score", 0.0), reverse=True)[:top_k]
