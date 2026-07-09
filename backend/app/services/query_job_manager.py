import json
from datetime import datetime

from app.core.config import QUERY_JOB_TTL_SECONDS
from app.core.redis import redis
from app.services.redis_client import redis_client


QUERY_JOB_STATUSES_ACTIVE = {"queued", "processing", "retrieving", "reranking", "generating"}


def utc_now() -> str:
    return datetime.utcnow().isoformat()


def create_query_job_sync(
    *,
    job_id: str,
    user_id: str,
    question: str,
    filters: dict,
    trace_id: str,
):
    now = utc_now()
    redis_client.hset(
        f"query_job:{job_id}",
        mapping={
            "job_id": job_id,
            "user_id": user_id,
            "question": question,
            "filters": json.dumps(filters),
            "trace_id": trace_id,
            "status": "queued",
            "progress": 0,
            "current_step": "queued",
            "answer": "",
            "citations": "[]",
            "retry_count": 0,
            "error": "",
            "created_at": now,
            "queued_at": now,
            "started_at": "",
            "updated_at": now,
            "completed_at": "",
            "failed_at": "",
            "route": "",
            "route_reason": "",
        },
    )
    redis_client.expire(f"query_job:{job_id}", QUERY_JOB_TTL_SECONDS)


async def create_query_job(**kwargs):
    create_query_job_sync(**kwargs)


def update_query_job_sync(job_id: str, **kwargs):
    kwargs["updated_at"] = utc_now()

    if "filters" in kwargs and isinstance(kwargs["filters"], dict):
        kwargs["filters"] = json.dumps(kwargs["filters"])

    if "citations" in kwargs and not isinstance(kwargs["citations"], str):
        kwargs["citations"] = json.dumps(kwargs["citations"])

    redis_client.hset(f"query_job:{job_id}", mapping=kwargs)
    redis_client.expire(f"query_job:{job_id}", QUERY_JOB_TTL_SECONDS)


async def update_query_job(job_id: str, **kwargs):
    kwargs["updated_at"] = utc_now()
    if "filters" in kwargs and isinstance(kwargs["filters"], dict):
        kwargs["filters"] = json.dumps(kwargs["filters"])
    if "citations" in kwargs and not isinstance(kwargs["citations"], str):
        kwargs["citations"] = json.dumps(kwargs["citations"])
    await redis.hset(f"query_job:{job_id}", mapping=kwargs)
    await redis.expire(f"query_job:{job_id}", QUERY_JOB_TTL_SECONDS)


def get_query_job_sync(job_id: str) -> dict:
    return redis_client.hgetall(f"query_job:{job_id}")


async def get_query_job(job_id: str) -> dict:
    return await redis.hgetall(f"query_job:{job_id}")


def increment_query_retry_count(job_id: str) -> int:
    retry_count = redis_client.hincrby(f"query_job:{job_id}", "retry_count", 1)
    redis_client.expire(f"query_job:{job_id}", QUERY_JOB_TTL_SECONDS)
    return int(retry_count)
