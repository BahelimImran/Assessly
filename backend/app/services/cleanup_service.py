import os
from collections import defaultdict

from qdrant_client.models import Filter, FieldCondition, MatchValue

from app.core.config import CHILD_COLLECTION, PARENT_COLLECTION, UPLOAD_DIR
from app.db.qdrant_client import collection_exists, qdrant
from app.services.metadata_repository import list_active_document_ids, list_referenced_upload_file_names

""" 
Gets all active document IDs from Postgres.
Scans Qdrant parent and child collections.
Finds Qdrant points whose document_id does not exist in Postgres.

Sometimes Qdrant may contain leftover vectors after:
    failed deletion
    manual DB change
    interrupted ingestion
    old development data
    migration from older design
 """
def find_orphaned_qdrant_document_ids() -> dict[str, list[str]]:
    active_document_ids = list_active_document_ids()
    orphaned_by_collection = defaultdict(set)

    for collection_name in [PARENT_COLLECTION, CHILD_COLLECTION]:
        if not collection_exists(collection_name):
            continue

        offset = None

        while True:
            points, offset = qdrant.scroll(
                collection_name=collection_name,
                offset=offset,
                limit=256,
                with_payload=True,
                with_vectors=False,
            )

            for point in points:
                payload = point.payload or {}
                document_id = payload.get("document_id")

                if document_id and document_id not in active_document_ids:
                    orphaned_by_collection[collection_name].add(document_id)

            if offset is None:
                break

    return {
        collection_name: sorted(document_ids)
        for collection_name, document_ids in orphaned_by_collection.items()
    }

""" 
Counts Qdrant parent/child points for a document.
If dry_run=True, only reports counts.
If dry_run=False, deletes those points.

Safe cleanup should first show what would be deleted.
 """
def delete_qdrant_document_points(document_id: str, dry_run: bool = True) -> dict[str, int]:
    deleted = {}

    qdrant_filter = Filter(
        must=[
            FieldCondition(
                key="document_id",
                match=MatchValue(value=document_id),
            )
        ]
    )

    for collection_name in [PARENT_COLLECTION, CHILD_COLLECTION]:
        if not collection_exists(collection_name):
            deleted[collection_name] = 0
            continue

        count = qdrant.count(
            collection_name=collection_name,
            count_filter=qdrant_filter,
            exact=True,
        ).count

        if count and not dry_run:
            qdrant.delete(
                collection_name=collection_name,
                points_selector=qdrant_filter,
            )

        deleted[collection_name] = count

    return deleted

""" 
What it does:

Lists files in UPLOAD_DIR.
Gets all upload file names referenced by Postgres upload sessions.
Returns files on disk that Postgres does not know about.

Why:
Upload folder may contain leftover files from:

failed upload
crash during upload
old development runs
deleted metadata
 """
def find_unreferenced_upload_files() -> list[str]:
    if not os.path.isdir(UPLOAD_DIR):
        return []

    referenced_file_names = list_referenced_upload_file_names()

    return [
        name
        for name in os.listdir(UPLOAD_DIR)
        if (
            os.path.isfile(os.path.join(UPLOAD_DIR, name))
            and name not in referenced_file_names
        )
    ]
