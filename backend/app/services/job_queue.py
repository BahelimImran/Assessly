from app.services.redis_client import redis_client
import json

JOB_QUEUE = "ingestion_jobs"

def enqueue_job(payload: dict):
    redis_client.rpush(JOB_QUEUE, json.dumps(payload))

def dequeue_job():
    _, job = redis_client.blpop(JOB_QUEUE)
    return json.loads(job)