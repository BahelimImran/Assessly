import math


def sigmoid(x: float) -> float:
    return 1 / (1 + math.exp(-x))


def safe_float(value, default=0.0):
    try:
        return float(value or default)
    except (TypeError, ValueError):
        return default


def average(values):
    return sum(values) / len(values) if values else 0.0


def calculate_confidence(chunks):
    if not chunks:
        return 0.0

    vector_scores = [safe_float(c.get("vector_score")) for c in chunks]
    bm25_scores = [safe_float(c.get("bm25_score")) for c in chunks]
    rrf_scores = [safe_float(c.get("rrf_score")) for c in chunks]
    rerank_scores = [safe_float(c.get("rerank_score")) for c in chunks]

    avg_vector = average(vector_scores)

    # BM25 is unbounded, normalize using max score from retrieved chunks
    max_bm25 = max(bm25_scores) if bm25_scores else 0.0
    bm25_conf = average([
        score / max_bm25 for score in bm25_scores
    ]) if max_bm25 > 0 else 0.0

    # RRF is usually small, normalize using max RRF from retrieved chunks
    max_rrf = max(rrf_scores) if rrf_scores else 0.0
    rrf_conf = average([
        score / max_rrf for score in rrf_scores
    ]) if max_rrf > 0 else 0.0

    # Reranker may be negative/positive, sigmoid makes it 0–1
    rerank_conf = average([
        sigmoid(score) for score in rerank_scores
    ])

    confidence = (
        avg_vector * 0.35 +
        rerank_conf * 0.35 +
        rrf_conf * 0.20 +
        bm25_conf * 0.10
    )

    return round(min(1.0, max(0.0, confidence)), 2)