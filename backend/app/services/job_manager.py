import json
from datetime import datetime

from app.core.redis import redis

class JobManager:

    @staticmethod
    async def create_job(job_id: str, user_id: str, file_name: str):

        await redis.hset(
            f"job:{job_id}",
            mapping={
                "job_id": job_id,
                "user_id": user_id,
                "file_name": file_name,
                "status": "queued",
                "progress": 0,
                "created_at": datetime.utcnow().isoformat()
            }
        )

        # await redis.expire(
        #     f"job:{job_id}",
        #     86400
        # )

    @staticmethod
    async def update_job(job_id: str, **kwargs):

        await redis.hset(
            f"job:{job_id}",
            mapping=kwargs
        )

        await redis.expire(
            f"job:{job_id}",
            86400
        )

    @staticmethod
    async def get_job(job_id: str):

        return await redis.hgetall(f"job:{job_id}")

    @staticmethod
    async def publish_log(
        job_id: str,
        message: str,
        progress: int = 0
    ):

        payload = {
            "message": message,
            "progress": progress
        }

        await redis.publish(
            f"job:{job_id}",
            json.dumps(payload)
        )