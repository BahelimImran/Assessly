from app.services.job_queue import dequeue_job
from app.core.config import UPLOAD_DIR
from app.services.pubsub_logger import publish_log
from app.services.rag_service import ingest_pdf
from app.services.redis_client import redis_client
import os


def update_job(job_id: str, **kwargs):
    redis_client.hset(f"job:{job_id}", mapping=kwargs)
    redis_client.expire(f"job:{job_id}", 86400)


while True:
    job = dequeue_job()

    file_name = job.get("file_name")
    file_path = job.get("file_path")
    job_id = job["job_id"]
    user_id = job["user_id"]

    if file_name:
        file_path = os.path.join(UPLOAD_DIR, file_name)

    def log(message, progress=10):
        publish_log(job_id, message, progress)

    try:
        update_job(job_id, status="processing", progress=10)
        publish_log(job_id, f"Ingestion started for user {user_id}", 10)

        ingest_pdf(
            file_path=file_path,
            log=log,
            user_id=user_id,
        )

        update_job(job_id, status="completed", progress=100)
        publish_log(job_id, "Ingestion completed", 100)

    except Exception as e:
        update_job(job_id, status="failed", progress=0, error=str(e))
        publish_log(job_id, f"Ingestion failed: {str(e)}", 0)
