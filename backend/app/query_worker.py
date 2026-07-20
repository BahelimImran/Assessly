import json
from datetime import datetime

from app.core.config import AUTO_CREATE_DB_TABLES
from app.db.postgres import init_db
from app.services.pubsub_logger import publish_query_event
from app.services.query_job_manager import (
    increment_query_retry_count,
    update_query_job_sync,
)
from app.services.query_queue import ack_query_job, dequeue_query_job
from app.services.rag_service import generate_answer, call_llm

from app.services.query_intension_router.hybrid_router import hybrid_router
from app.services.model_client import post_json_with_retry
import logging
from app.core.config import *

from app.services.answer_verification.verify_agent import verify_answer


logger = logging.getLogger("router")

if AUTO_CREATE_DB_TABLES:
    init_db()


def utc_now() -> str:
    return datetime.utcnow().isoformat()


def fail_query_job(job: dict, message: str):
    job_id = job.get("job_id", "")
    user_id = job.get("user_id", "")
    trace_id = job.get("trace_id", "")

    if job_id:
        update_query_job_sync(
            job_id,
            status="failed",
            current_step="failed",
            progress=0,
            error=message,
            failed_at=utc_now(),
        )
        publish_query_event(
            job_id=job_id,
            user_id=user_id,
            trace_id=trace_id,
            status="failed",
            level="error",
            message=message,
        )

    stream_id = job.get("stream_id")
    if stream_id:
        ack_query_job(stream_id)


def process_query_job(job: dict):
    job_id = job.get("job_id")
    user_id = job.get("user_id")
    question = job.get("question")
    trace_id = job.get("trace_id", job_id)

    if not job_id or not user_id or not question:
        fail_query_job(job, "Invalid query job payload.")
        return

    filters = job.get("filters") or {}
    if isinstance(filters, str):
        filters = json.loads(filters or "{}")

    filters["user_id"] = user_id

    retry_count = increment_query_retry_count(job_id)
    update_query_job_sync(
        job_id,
        status="processing",
        current_step="processing",
        progress=10,
        retry_count=retry_count,
        started_at=utc_now(),
        error="",
    )
    publish_query_event(
        job_id=job_id,
        user_id=user_id,
        trace_id=trace_id,
        status="processing",
        message="Query processing started",
    )

    result, route_info = generate_answer_basedon_query_intension(job, filters, job_id, user_id, trace_id, question)
    if result is None:
     result = {}

    if route_info is None:
        route_info = {}

    if result and route_info :
        citations = result.get("citations") or result.get("sources") or []
    else :
        citations = []

    update_query_job_sync(
        job_id,
        status="completed",
        current_step="completed",
        progress=100,
        answer=result.get("answer", "") if result else None,
        citations=citations,
        completed_at=utc_now(),
        error="",
    )
    publish_query_event(
        job_id=job_id,
        user_id=user_id,
        trace_id=trace_id,
        status="completed",
        message="Query completed",
    )

    stream_id = job.get("stream_id")
    if stream_id:
        ack_query_job(stream_id)

    logger.info({
    "query": question,
    "route": route_info["route"] if route_info else None,
    "confidence": route_info.get("confidence") if route_info else None,
    "reason": route_info["reason"] if route_info else None
    })
    

def generate_answer_basedon_query_intension(job:dict, filters:dict, job_id: str, user_id: str, trace_id: str, question: str):
    
    def progress(status: str, message: str):
        progress_map = {
            "routing": 15,
            "retrieving": 30,
            "reranking": 55,
            "generating": 75,
        }
        update_query_job_sync(
            job_id,
            status=status,
            current_step=status,
            progress=progress_map.get(status, 20),
        )
        publish_query_event(
            job_id=job_id,
            user_id=user_id,
            trace_id=trace_id,
            status=status,
            message=message,
        )
    try:
        # 🧠 ROUTING STEP
        route_info = hybrid_router(question)

        update_query_job_sync(
            job_id,
            route=route_info["route"],
            route_reason=route_info["reason"]
        )

        publish_query_event(
            job_id=job_id,
            user_id=user_id,
            trace_id=trace_id,
            status="routing",
            message=f"Routing → {route_info['route']} ({route_info['reason']})"
        )

        # NO_RAG FLOW
        if route_info["route"] == "NO_RAG":

            update_query_job_sync(
                job_id,
                status="generating",
                current_step="generating",
                progress=70
            )

            publish_query_event(
                job_id=job_id,
                user_id=user_id,
                trace_id=trace_id,
                status="generating",
                message="NO_RAG Flow - Generating direct LLM response"
            )

            # result = {
            #     "answer": "",
            #     "citations": []
            # }
            # result['answer'] = call_llm(question)

            result = generate_answer( question, None, progress_callback=progress )

        # RAG FLOW
        else:
            
            update_query_job_sync(
                job_id,
                status="generating",
                current_step="generating",
                progress=70
            )

            publish_query_event(
                job_id=job_id,
                user_id=user_id,
                trace_id=trace_id,
                status="generating",
                message="RAG Flow - Generating LLM response"
            )

            result = generate_answer(
                question,
                filters,
                progress_callback=progress
            )

        return result, route_info
        

    except Exception as exc:
        fail_query_job(job, str(exc))
        return None, None 
    

while True:
    query_job = dequeue_query_job()
    if not query_job:
        continue

    process_query_job(query_job)
