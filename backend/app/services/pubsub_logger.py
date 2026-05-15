from app.services.redis_client import redis_client
import json

def publish_log(job_id: str, message: str):

    redis_client.publish(
        f"logs:{job_id}",
        json.dumps({
            "job_id": job_id,
            "message": message
        })
    )