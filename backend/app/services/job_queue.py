import json
import socket
import uuid

from redis.exceptions import ResponseError
from opentelemetry.propagate import inject

from app.core.config import JOB_STREAM_BLOCK_MS, JOB_STREAM_RECLAIM_IDLE_MS
from app.core.tracing import tracer
from app.services.redis_client import redis_client
from opentelemetry import context

from app.core.langfuse import get_langfuse, get_trace_context

JOB_STREAM = "ingestion_jobs"
JOB_GROUP = "ingestion_workers"
CONSUMER_NAME = f"{socket.gethostname()}-{uuid.uuid4()}"


def ensure_consumer_group():
    try:
        redis_client.xgroup_create(
            name=JOB_STREAM,
            groupname=JOB_GROUP,
            id="0",
            mkstream=True,
        )
    except ResponseError as exc:
        if "BUSYGROUP" not in str(exc):
            raise


def enqueue_job(payload: dict):
    ensure_consumer_group()

    with tracer.start_as_current_span("queue.enqueue_job") as span:
        span.set_attribute("job.id", payload.get("job_id", ""))
        span.set_attribute("job.user_id", payload.get("user_id", ""))
        span.set_attribute("queue.name", JOB_STREAM)

        carrier = {}
        inject(carrier, context=context.get_current())  # ✅ explicit context
        payload["trace_context"] = carrier

        span.add_event("inject_trace_context")

        trace_ctx = get_trace_context() # langfuse
        payload["trace_id"] = trace_ctx["trace_id"]
        payload["span_id"] = trace_ctx["span_id"]

        stream_id = redis_client.xadd(
            JOB_STREAM,
            {
                "job_id": payload["job_id"],
                "user_id": payload["user_id"],
                "payload": json.dumps(payload),
            },
        )

        span.set_attribute("job.stream_id", str(stream_id))
        span.add_event("job_enqueued")

        return stream_id


def _decode_stream_message(stream_id, fields: dict) -> dict:
    payload = json.loads(fields.get("payload", "{}"))
    payload["stream_id"] = stream_id
    return payload


def _claim_stale_job() -> dict | None:
    claimed = redis_client.xautoclaim(
        name=JOB_STREAM,
        groupname=JOB_GROUP,
        consumername=CONSUMER_NAME,
        min_idle_time=JOB_STREAM_RECLAIM_IDLE_MS,
        start_id="0-0",
        count=1,
    )

    messages = claimed[1] if isinstance(claimed, tuple) and len(claimed) > 1 else []
    if not messages:
        return None

    stream_id, fields = messages[0]
    return _decode_stream_message(stream_id, fields)


def dequeue_job() -> dict | None:
    ensure_consumer_group()

    stale_job = _claim_stale_job()
    if stale_job:
        return stale_job

    response = redis_client.xreadgroup(
        groupname=JOB_GROUP,
        consumername=CONSUMER_NAME,
        streams={JOB_STREAM: ">"},
        count=1,
        block=JOB_STREAM_BLOCK_MS,
    )

    if not response:
        return None

    lf_trace = None  # ✅ FIX: define early

    try:
        # ✅ Extract message properly
        stream_name, messages = response[0]
        stream_id, fields = messages[0]

        decoded = _decode_stream_message(stream_id, fields)

        trace_id = decoded.get("trace_id")  # ✅ correct place

        # ✅ Langfuse tracing
        langfuse = get_langfuse()
        lf_trace = langfuse.trace(
            id=trace_id,
            name="ingestion_worker",
            input=decoded
        )

        # 👉 your ingestion logic here
        # process_job(decoded)

        lf_trace.update(
            output={"status": "success"}
        )

        # lf_trace.flush()

        return decoded

    except Exception as e:
        if lf_trace:  # ✅ FIX: guard check
            lf_trace.update(
                level="ERROR",
                status_message=str(e)
            )
        raise


def ack_job(stream_id: str):
    redis_client.xack(JOB_STREAM, JOB_GROUP, stream_id)