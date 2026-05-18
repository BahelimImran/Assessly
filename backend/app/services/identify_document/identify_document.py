import hashlib
from pathlib import Path

from qdrant_client.models import Filter, FieldCondition, MatchValue

from app.db.qdrant_client import qdrant
# from app.core.config import QDRANT_COLLECTION


def hash_text(text: str) -> str:
    """
    Creates stable hash for chunk text.
    Same chunk text = same hash.
    """
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def hash_file_bytes(file_path: str) -> str:
    """
    Creates stable document hash from actual file content.
    Same content = same hash, even if filename changes.
    """
    file_path = Path(file_path)

    sha256 = hashlib.sha256()

    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            sha256.update(chunk)

    return sha256.hexdigest()


def clean_metadata(meta: dict) -> dict:
    """
    Qdrant payload metadata supports scalar values well.
    Avoid None, dict, list unless intentionally serialized.
    """

    cleaned = {}

    for key, value in meta.items():
        if value is None:
            continue

        if isinstance(value, (str, int, float, bool)):
            cleaned[key] = value
        else:
            cleaned[key] = str(value)

    return cleaned


# def build_document_filter(document_id: str) -> Filter:
#     """
#     Build Qdrant filter for one document.
#     """

#     return Filter(
#         must=[
#             FieldCondition(
#                 key="document_id",
#                 match=MatchValue(value=document_id)
#             )
#         ]
#     )


# def delete_existing_document(document_id: str) -> int:
#     """
#     Delete all existing chunks/vectors for a document.
#     Prevents duplicate chunks when the same document is uploaded again.
#     """

#     doc_filter = build_document_filter(document_id)

#     count_result = qdrant.count(
#         collection_name=QDRANT_COLLECTION,
#         count_filter=doc_filter,
#         exact=True
#     )

#     existing_count = count_result.count

#     if existing_count > 0:
#         qdrant.delete(
#             collection_name=QDRANT_COLLECTION,
#             points_selector=doc_filter
#         )

#     return existing_count