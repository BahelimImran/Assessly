def enrich_chunk(chunk):
    context = f"[{chunk.metadata['file']} > {chunk.metadata['section']}]"

    enriched_text = f"{context}\n\n{chunk.content}"

    chunk.content = enriched_text # why chunk.content present like this

    return chunk