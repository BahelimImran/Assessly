import asyncio
import logging

from fastapi import APIRouter, HTTPException
from app.core.config import QUERY_RATE_LIMIT_PER_MINUTE, RATE_LIMIT_WINDOW_SECONDS
from app.models.schema import QueryRequest
from app.services.rag_service import generate_answer
from app.services.rate_limiter import enforce_fixed_window_rate_limit

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/")
async def query(req: QueryRequest):
    try:
        rate_limit_subject = req.user_id or "anonymous"
        await enforce_fixed_window_rate_limit(
            subject=rate_limit_subject,
            action="query",
            limit=QUERY_RATE_LIMIT_PER_MINUTE,
            window_seconds=RATE_LIMIT_WINDOW_SECONDS,
        )

        filters = {
            "document_id": req.document_id,
            "file_name": req.file_name,
            "page": req.page,
            "section": req.section,
            "chunk_type": req.chunk_type,
            "upload_session_id": req.upload_session_id,
            "user_id": req.user_id,
        }

        result = await asyncio.to_thread(generate_answer, req.question, filters)

        return {
            "question": req.question,
            **result, # dictionary unpacking
            "filters_applied": filters
        }
    except HTTPException: #Keeps HTTPException as-is so 429 does not become 500.
        raise

    except Exception as e:
        logger.exception("Query failed")
        raise HTTPException(
            status_code=500,
            detail=f"Query failed: {str(e)}"
        )

