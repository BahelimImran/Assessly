from app.services.redis_client import redis_client
import json
from datetime import datetime


def utc_now() -> str:
    return datetime.utcnow().isoformat()

def publish_log(job_id: str, message: str, progress: int = 0):

    redis_client.publish(
        f"logs:{job_id}",
        json.dumps({
            "job_id": job_id,
            "message": message,
            "progress": progress
        })
    )


def publish_query_event(
    *,
    job_id: str,
    user_id: str,
    trace_id: str,
    status: str,
    message: str,
    level: str = "info",
    component: str = "query_worker",
):
    redis_client.publish(
        f"query_logs:{job_id}",
        json.dumps({
            "timestamp": utc_now(),
            "level": level,
            "trace_id": trace_id,
            "job_id": job_id,
            "user_id": user_id,
            "component": component,
            "status": status,
            "message": message,
        })
    )
