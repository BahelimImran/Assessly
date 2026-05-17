from fastapi import APIRouter, Depends, HTTPException
from qdrant_client.models import Filter, FieldCondition, MatchValue

from app.db.qdrant_client import qdrant
from app.db.qdrant_client import delete_existing_document
from app.core.config import CHILD_COLLECTION
from app.services.auth_dependencies import AuthPrincipal, allow_guest_query_only, require_user
from app.services.metadata_repository import list_user_documents, mark_document_deleted


router = APIRouter()


@router.get("/files")
def list_ingested_files(
    tenant_id: str,
    principal: AuthPrincipal = Depends(allow_guest_query_only),
):
    try:
        user_id = principal.user_id
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


@router.delete("/files/{document_id}")
def delete_ingested_file(
    document_id: str,
    principal: AuthPrincipal = Depends(require_user),
):
    try:
        user_id = principal.user_id
        deleted_document = mark_document_deleted(document_id, user_id)

        if not deleted_document:
            raise HTTPException(
                status_code=404,
                detail="Document not found"
            )

        deleted_vectors = delete_existing_document(document_id, user_id)

        return {
            "status": "deleted",
            "document_id": document_id,
            "deleted_vectors": deleted_vectors
        }

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete document: {str(e)}"
        )
