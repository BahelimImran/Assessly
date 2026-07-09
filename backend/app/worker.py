import os
from datetime import datetime

from opentelemetry.propagate import extract
from opentelemetry.trace import Status, StatusCode

from app.core.config import AUTO_CREATE_DB_TABLES, JOB_TTL_SECONDS, UPLOAD_DIR
from app.core.tracing import tracer, mark_span_error
from app.db.qdrant_client import delete_upload_session_points
from app.db.postgres import init_db
from app.services.job_queue import ack_job, dequeue_job
from app.services.metadata_repository import (
    mark_ingestion_completed,
    mark_ingestion_failed,
    mark_ingestion_started,
    update_ingestion_progress,
)
from app.services.pubsub_logger import publish_log
from app.services.rag_service import ingest_pdf
from app.services.redis_client import redis_client

from opentelemetry.instrumentation.redis import RedisInstrumentor
RedisInstrumentor().instrument()  # auto-traces redis calls made inside the worker too

if AUTO_CREATE_DB_TABLES:
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


def fail_job(job_id: str, message: str, stream_id: str | None = None, span=None):
    update_job(
        job_id,
        status="failed",
        progress=0,
        current_step="failed",
        error=message,
        failed_at=utc_now(),
    )
    mark_ingestion_failed(job_id, message)
    publish_log(job_id, f"Ingestion failed: {message}", 0)

    if span:
        span.set_attribute("job.status", "failed")
        span.set_status(Status(StatusCode.ERROR, message))

    if stream_id:
        ack_job(stream_id)


while True:
    job = dequeue_job()
    if not job:
        continue

    stream_id = job.get("stream_id")
    job_id = job.get("job_id")
    user_id = job.get("user_id")
    document_id = job.get("document_id")
    document_hash = job.get("document_hash")
    upload_session_id = job.get("upload_session_id")
    previous_active_upload_session_id = job.get("previous_active_upload_session_id")
    file_path = resolve_file_path(job)

    # Why:
    # If the producer attached a traceparent, this resumes the SAME trace
    # that started when the API accepted the upload. If not present
    # (e.g. old jobs still in the stream from before this change),
    # extract() just returns an empty context and a fresh trace starts —
    # nothing breaks either way.
    # carrier = {"traceparent": job.get("traceparent", "")}
    # parent_ctx = extract(carrier)

    parent_ctx = extract(job.get("trace_context", {}))

    with tracer.start_as_current_span("worker.process_job", context=parent_ctx) as span:
        span.add_event("job_received")
        span.set_attribute("job.id", job_id or "")
        span.set_attribute("job.user_id", user_id or "")
        span.set_attribute("job.document_id", document_id or "")

        with tracer.start_as_current_span("worker.validate_job"):
            if not job_id:
                if stream_id:
                    ack_job(stream_id)
                continue

            if not user_id:
                fail_job(job_id, "Invalid job payload: missing user_id.", stream_id, span)
                continue

            if not file_path:
                fail_job(job_id, "Invalid job payload: missing file reference.", stream_id, span)
                continue

            if not os.path.exists(file_path):
                fail_job(job_id, f"Uploaded file not found for worker: {file_path}", stream_id, span)
                continue

        def log(message, progress=10):
            publish_log(job_id, message, progress)
            update_job(job_id, current_step=message, progress=progress)
            update_ingestion_progress(job_id, message, progress)

        try:
            
            retry_count = increment_retry_count(job_id)
            span.set_attribute("job.retry_count", retry_count)
            mark_ingestion_started(job_id, retry_count)
            update_job(
                job_id,
                status="processing",
                progress=10,
                current_step="processing",
                error="",
                started_at=utc_now(),
            )
            publish_log(job_id, f"Ingestion started for document: {document_id}", 10)

            with tracer.start_as_current_span("worker.ingest_pdf") as ingest_span:
                ingest_span.set_attribute("document.id", document_id or "")
                ingest_span.set_attribute("file.path", file_path or "")
                span.add_event("job_started")
                
                result = ingest_pdf(
                    file_path=file_path,
                    log=log,
                    user_id=user_id,
                    document_id=document_id,
                    document_hash=document_hash,
                    upload_session_id=upload_session_id,
                )
                
                ingest_span.set_attribute("chunks_created", int(result.get("chunks", 0)))
                span.add_event("job_completed")
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
            span.set_attribute("job.status", "completed")

            if previous_active_upload_session_id:
                with tracer.start_as_current_span("worker.cleanup_previous_version") as cleanup_span:
                    cleanup_span.set_attribute(
                        "previous_upload_session_id",
                        previous_active_upload_session_id
                    )
                    deleted = delete_upload_session_points(previous_active_upload_session_id, user_id)
                    publish_log(job_id, f"Cleaned previous document version: {deleted} and updated fresh information", 100)

            if stream_id:
                ack_job(stream_id)

        except Exception as e:
            mark_span_error(span, e)
            fail_job(job_id, str(e), stream_id, span)
            span.add_event("job_failed", {"error": str(e)})