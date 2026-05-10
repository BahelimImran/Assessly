from qdrant_client.models import Filter, FieldCondition, MatchAny

from app.db.qdrant_client import qdrant
from app.core.config import PARENT_COLLECTION


def fetch_parent_chunks(parent_ids: list[str]) -> list[dict]:
    if not parent_ids:
        return []

    qdrant_filter = Filter(
        must=[
            FieldCondition(
                key="parent_id",
                match=MatchAny(any=parent_ids)
            )
        ]
    )

    points, _ = qdrant.scroll(
        collection_name=PARENT_COLLECTION,
        scroll_filter=qdrant_filter,
        limit=len(parent_ids),
        with_payload=True,
        with_vectors=False
    )

    parent_map = {}

    for point in points:
        payload = point.payload or {}

        parent_id = payload.get("parent_id")

        parent_map[parent_id] = {
            "id": point.id,
            "parent_id": payload.get("parent_id"),
            "content": payload.get("full_text", ""),
            "section_title": payload.get("section_title", ""),
            "document_id": payload.get("document_id"),
            "payload": payload,
        }

    ordered_parents = []

    for parent_id in parent_ids:
        parent = parent_map.get(parent_id)
        if parent:
            ordered_parents.append(parent)

    return ordered_parents