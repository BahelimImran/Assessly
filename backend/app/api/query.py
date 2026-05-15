from fastapi import APIRouter, HTTPException
from app.models.schema import QueryRequest
from app.services.rag_service import generate_answer
import traceback

router = APIRouter()


@router.post("/")
def query(req: QueryRequest):
    try:
        filters = {
            "document_id": req.document_id,
            "file_name": req.file_name,
            "page": req.page,
            "section": req.section,
            "chunk_type": req.chunk_type,
            "upload_session_id": req.upload_session_id,
            "user_id": req.user_id,
        }

        result = generate_answer(req.question, filters)

        return {
            "question": req.question,
            **result, # dictionary unpacking
            "filters_applied": filters
        }
    except Exception as e:
        print("Query Error:\n")
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Query failed: {str(e)}"
        )

