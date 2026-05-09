from typing import List, Dict, Any


def compress_context_chunks(
    chunks: List[Dict[str, Any]],
    max_chars: int = 12000,
    max_chunk_chars: int = 3000,
) -> List[Dict[str, Any]]:
    """
    Simple deterministic context compression.
    Keeps reranked order, preserves metadata, and trims very large text chunks.
    Tables are kept more intact because partial tables reduce answer quality.
    """
    compressed = []
    used_chars = 0

    for item in chunks:
        content = (item.get("content") or "").strip()
        if not content:
            continue

        chunk_type = (item.get("metadata") or {}).get("chunk_type", "text")
        allowed_chars = max_chunk_chars

        if chunk_type == "table":
            allowed_chars = min(max_chunk_chars * 2, 6000)

        if len(content) > allowed_chars:
            content = content[:allowed_chars].rstrip() + "\n...[compressed]"

        if used_chars + len(content) > max_chars:
            remaining = max_chars - used_chars
            if remaining < 800:
                break
            content = content[:remaining].rstrip() + "\n...[context limit reached]"

        copied = dict(item)
        copied["content"] = content
        compressed.append(copied)
        used_chars += len(content)

    return compressed
