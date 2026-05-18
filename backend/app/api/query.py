import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sse_starlette.sse import EventSourceResponse

from app.core.config import GUEST_QUERY_RATE_LIMIT_PER_MINUTE, QUERY_RATE_LIMIT_PER_MINUTE, RATE_LIMIT_WINDOW_SECONDS
from app.core.redis import redis
from app.models.schema import QueryRequest
from app.services.auth_dependencies import AuthPrincipal, allow_guest_query_only
from app.services.query_job_manager import create_query_job, get_query_job
from app.services.query_queue import enqueue_query_job
from app.services.rate_limiter import enforce_fixed_window_rate_limit


router = APIRouter()


def _parse_query_job(job: dict) -> dict:
    return {
        **job,
        "progress": int(job.get("progress") or 0),
        "retry_count": int(job.get("retry_count") or 0),
    }


@router.post("/")
async def query(
    req: QueryRequest,
    principal: AuthPrincipal = Depends(allow_guest_query_only),
):
    try:
        rate_limit = GUEST_QUERY_RATE_LIMIT_PER_MINUTE if principal.is_guest else QUERY_RATE_LIMIT_PER_MINUTE
        await enforce_fixed_window_rate_limit(
            subject=principal.user_id,
            action="query",
            limit=rate_limit,
            window_seconds=RATE_LIMIT_WINDOW_SECONDS,
        )

        query_job_id = str(uuid.uuid4())
        trace_id = str(uuid.uuid4())
        filters = {
            "document_id": req.document_id,
            "file_name": req.file_name,
            "page": req.page,
            "section": req.section,
            "chunk_type": req.chunk_type,
            "upload_session_id": req.upload_session_id,
            "user_id": principal.user_id,
        }

        await create_query_job(
            job_id=query_job_id,
            user_id=principal.user_id,
            question=req.question,
            filters=filters,
            trace_id=trace_id,
        )
        enqueue_query_job({
            "job_id": query_job_id,
            "user_id": principal.user_id,
            "question": req.question,
            "filters": filters,
            "trace_id": trace_id,
        })

        return {
            "query_job_id": query_job_id,
            "status": "queued",
            "trace_id": trace_id,
        }

    except HTTPException:
        raise

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to queue query: {str(exc)}",
        )


@router.get("/jobs/{query_job_id}")
async def get_query_job_status(
    query_job_id: str,
    principal: AuthPrincipal = Depends(allow_guest_query_only),
):
    job = await get_query_job(query_job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Query job not found")

    if job.get("user_id") != principal.user_id and not principal.is_admin:
        raise HTTPException(status_code=403, detail="You cannot access this query job")

    return _parse_query_job(job)


@router.get("/jobs/{query_job_id}/stream")
async def stream_query_job(
    query_job_id: str,
    request: Request,
    principal: AuthPrincipal = Depends(allow_guest_query_only),
):
    job = await get_query_job(query_job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Query job not found")

    if job.get("user_id") != principal.user_id and not principal.is_admin:
        raise HTTPException(status_code=403, detail="You cannot access this query job stream")

    async def event_generator():
        pubsub = redis.pubsub()
        channel = f"query_logs:{query_job_id}"
        await pubsub.subscribe(channel)

        try:
            while True:
                if await request.is_disconnected():
                    break

                message = await pubsub.get_message(
                    ignore_subscribe_messages=True,
                    timeout=5,
                )

                if message:
                    yield {
                        "event": "message",
                        "data": message["data"],
                    }

                else:
                    latest_job = await get_query_job(query_job_id)
                    if latest_job and latest_job.get("status") in {"completed", "failed"}:
                        yield {
                            "event": "message",
                            "data": "{}",
                        }
                        break

                    yield {
                        "event": "ping",
                        "data": "keepalive",
                    }

        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.close()

    return EventSourceResponse(event_generator())
