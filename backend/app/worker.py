import os
from datetime import datetime

from app.core.config import JOB_TTL_SECONDS, UPLOAD_DIR
from app.db.postgres import init_db #New Postgres Init Import
from app.services.job_queue import ack_job, dequeue_job

# These functions update Postgres durable state.

# Why:
# Redis is temporary/live progress. Postgres is durable history.
from app.services.metadata_repository import (
    mark_ingestion_completed,
    mark_ingestion_failed,
    mark_ingestion_started,
    update_ingestion_progress,
)
from app.services.pubsub_logger import publish_log
from app.services.rag_service import ingest_pdf
from app.services.redis_client import redis_client

# What it does:
# Auto-creates missing metadata tables when worker starts.

# Why:
# Development convenience. Since worker runs in Docker, this prevents worker from failing if tables do not exist yet.

init_db()


def utc_now() -> str:
    return datetime.utcnow().isoformat()


def update_job(job_id: str, **kwargs):
    kwargs["updated_at"] = utc_now()
    redis_client.hset(f"job:{job_id}", mapping=kwargs)
    redis_client.expire(f"job:{job_id}", JOB_TTL_SECONDS)


def increment_retry_count(job_id: str) -> int:
    retry_count = redis_client.hincrby(f"job:{job_id}", "retry_count", 1)
    redis_client.expire(f"job:{job_id}", JOB_TTL_SECONDS)
    return int(retry_count)


def resolve_file_path(job: dict) -> str | None:
    file_name = job.get("file_name")
    file_path = job.get("file_path")

    if file_name:
        return os.path.join(UPLOAD_DIR, file_name)

    return file_path


def fail_job(job_id: str, message: str, stream_id: str | None = None):
    update_job(
        job_id,
        status="failed",
        progress=0,
        current_step="failed",
        error=message,
        failed_at=utc_now(),
    )

# When worker marks Redis job as failed, it also marks Postgres job/document/upload session as failed.

# Why:
# If Redis expires later, Postgres still knows the job failed and why.
    mark_ingestion_failed(job_id, message)
    publish_log(job_id, f"Ingestion failed: {message}", 0)

    if stream_id:
        ack_job(stream_id)


while True:
    job = dequeue_job()
    if not job:
        continue
# These values come from ingest.py queue payload.
    stream_id = job.get("stream_id")
    job_id = job.get("job_id")
    user_id = job.get("user_id")
    document_id = job.get("document_id")
    document_hash = job.get("document_hash")
    upload_session_id = job.get("upload_session_id")
    file_path = resolve_file_path(job)

    if not job_id:
        if stream_id:
            ack_job(stream_id)
        continue

    if not user_id:
        fail_job(job_id, "Invalid job payload: missing user_id.", stream_id)
        continue

    if not file_path:
        fail_job(job_id, "Invalid job payload: missing file reference.", stream_id)
        continue

    if not os.path.exists(file_path):
        fail_job(job_id, f"Uploaded file not found for worker: {file_path}", stream_id)
        continue

    def log(message, progress=10):

# SSE logs still go through Redis pub/sub
# Redis job status still updates
# Postgres durable job progress also updates

# Why:
# Redis gives live UI updates. Postgres keeps durable progress history.       
       
        publish_log(job_id, message, progress)
        update_job(job_id, current_step=message, progress=progress)
        update_ingestion_progress(job_id, message, progress)

    try:
        retry_count = increment_retry_count(job_id)
        mark_ingestion_started(job_id, retry_count)
        update_job(
            job_id,
            status="processing",
            progress=10,
            current_step="processing",
            error="",
            started_at=utc_now(),
        )
        publish_log(job_id, f"Ingestion started for user {user_id}", 10)

        result = ingest_pdf(
            file_path=file_path,
            log=log,
            user_id=user_id,
            document_id=document_id,
            document_hash=document_hash,
            upload_session_id=upload_session_id,
        )

        update_job(
            job_id,
            status="completed",
            progress=100,
            current_step="completed",
            completed_at=utc_now(),
            error="",
            retry_count=retry_count,
        )
        mark_ingestion_completed(job_id, int(result.get("chunks", 0)))
        publish_log(job_id, "Ingestion completed", 100)

        if stream_id:
            ack_job(stream_id)

    except Exception as e:
        fail_job(job_id, str(e), stream_id)
