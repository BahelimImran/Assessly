from app.services.job_queue import dequeue_job
from app.services.rag_service import ingest_pdf
from app.services.pubsub_logger import publish_log

while True:

    job = dequeue_job()

    file_path = job["file_path"]
    job_id = job["job_id"]
    user_id = job["user_id"]

    def log(message):
        publish_log(job_id, message)

    try:
        ingest_pdf(
            file_path=file_path,
            log=log,
            user_id=user_id
        )

        publish_log(job_id, "✅ Ingestion completed")

    except Exception as e:
        publish_log(job_id, f"❌ {str(e)}")