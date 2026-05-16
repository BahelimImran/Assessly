from fastapi import APIRouter, HTTPException
from qdrant_client.models import Filter, FieldCondition, MatchValue

from app.db.qdrant_client import qdrant
from app.core.config import CHILD_COLLECTION
from app.models.schema import QueryRequest
from app.services.metadata_repository import list_user_documents


router = APIRouter()


@router.get("/files")
def list_ingested_files(
    tenant_id: str,
    user_id: str
):
    try:
        print(f"knowledge api user-id :{user_id}")
        metadata_files = list_user_documents(user_id, ready_only=True)
        if metadata_files:
            return {
                "files": metadata_files
            }

        points, _ = qdrant.scroll(
            collection_name=CHILD_COLLECTION,
            scroll_filter=Filter(
                must=[
                    # FieldCondition(key="tenant_id", match=MatchValue(value=tenant_id)),
                    FieldCondition(key="user_id", match=MatchValue(value=user_id)),
                ]
            ),
            limit=10000,
            with_payload=True,
            with_vectors=False
        )

        files = {}

        for point in points:
            payload = point.payload or {}

            document_id = payload.get("document_id")
            source_file = payload.get("source_file")
            extract_filename = source_file.split('##')[1]

            if not document_id or not source_file:
                continue

            if document_id not in files:
                files[document_id] = {
                    "document_id": document_id,
                    "source_file": extract_filename,
                    "chunk_count": 0
                }

            files[document_id]["chunk_count"] += 1

        return {
            "files": list(files.values())
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load knowledge base files: {str(e)}"
        )
