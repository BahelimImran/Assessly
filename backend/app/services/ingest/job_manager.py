import asyncio
from datetime import datetime


class JobManager:
    def __init__(self):
        self.jobs = {}

    def create_job(self, job_id: str):
        self.jobs[job_id] = {
            "queue": asyncio.Queue(),
            "status": "queued",
            "created_at": datetime.utcnow().isoformat(),
            "started_at": None,
            "completed_at": None,
            "error": None,
            "progress": 0,
            "current_step": "Waiting..."
        }

    def get_job(self, job_id: str):
        return self.jobs.get(job_id)

    async def push_log(self, job_id: str, message: str):
        job = self.get_job(job_id)

        if not job:
            return

        await job["queue"].put(message)

    def update_status(
        self,
        job_id: str,
        *,
        status=None,
        progress=None,
        current_step=None,
        error=None
    ):
        job = self.get_job(job_id)

        if not job:
            return

        if status:
            job["status"] = status

            if status == "processing":
                job["started_at"] = datetime.utcnow().isoformat()

            if status in ["completed", "failed"]:
                job["completed_at"] = datetime.utcnow().isoformat()

        if progress is not None:
            job["progress"] = progress

        if current_step:
            job["current_step"] = current_step

        if error:
            job["error"] = error


job_manager = JobManager()