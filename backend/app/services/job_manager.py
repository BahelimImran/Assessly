import json
from datetime import datetime

from app.core.config import JOB_TTL_SECONDS
from app.core.redis import redis


ACTIVE_JOB_STATUSES = {"queued", "processing"}


def utc_now() -> str:
    return datetime.utcnow().isoformat()


class JobManager:

    @staticmethod
    async def create_job(job_id: str, user_id: str, file_name: str, safe_file_name: str):
        now = utc_now()

        await redis.hset(
            f"job:{job_id}",
            mapping={
                "job_id": job_id,
                "user_id": user_id,
                "file_name": file_name,
                "safe_file_name": safe_file_name,
                "status": "queued",
                "progress": 0,
                "current_step": "queued",
                "error": "",
                "retry_count": 0,
                "created_at": now,
                "queued_at": now,
                "started_at": "",
                "updated_at": now,
                "completed_at": "",
                "failed_at": "",
            }
        )

        await redis.expire(f"job:{job_id}", JOB_TTL_SECONDS)

    @staticmethod
    async def update_job(job_id: str, **kwargs):
        kwargs["updated_at"] = utc_now()

        await redis.hset(
            f"job:{job_id}",
            mapping=kwargs
        )

        await redis.expire(
            f"job:{job_id}",
            JOB_TTL_SECONDS
        )

    @staticmethod
    async def get_job(job_id: str):

        return await redis.hgetall(f"job:{job_id}")

    @staticmethod
    async def count_active_jobs_for_user(user_id: str) -> int:
        active_count = 0

        async for key in redis.scan_iter("job:*"):
            job = await redis.hgetall(key)
            if (
                job.get("user_id") == user_id
                and job.get("status") in ACTIVE_JOB_STATUSES
            ):
                active_count += 1

        return active_count

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
            f"logs:{job_id}",
            json.dumps(payload)
        )
