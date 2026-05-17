from fastapi import APIRouter, HTTPException, Request, UploadFile, File, Form
from sse_starlette.sse import EventSourceResponse
import os
import asyncio
import uuid
# from app.services.ingest.job_manager import job_manager

from app.core.config import UPLOAD_DIR
from app.core.config import MAX_UPLOAD_SIZE_BYTES, MAX_UPLOAD_SIZE_MB
from app.core.config import MAX_ACTIVE_JOBS_PER_USER
from app.services.upload_validator import (
    validate_pdf_file,
    validate_file_size,
    validate_pdf_page_count,
    calculate_file_hash,
)
from app.db.qdrant_client import document_exists
import json
from app.core.redis import redis
from app.services.job_manager import JobManager

from app.services.job_queue import enqueue_job
from app.services.metadata_repository import get_document_by_hash, prepare_upload_metadata



router = APIRouter()

os.makedirs(UPLOAD_DIR, exist_ok=True)

# log_queue = asyncio.Queue()


# 🔥 Modified ingestion wrapper (push logs)
# async def ingest_with_logs(file_path: str):
#     loop = asyncio.get_event_loop()

#     def log(message: str):
#         asyncio.run_coroutine_threadsafe(log_queue.put(message), loop)

#     await log_queue.put("✔️ 📥 Ingesting document...")

#     result = await loop.run_in_executor(
#         None,
#         ingest_pdf,
#         file_path,
#         log
#     )

#     await log_queue.put("✅ All set! You can start asking questions now.")

#     return result

async def _deprecated_ingest_with_logs(job_id: str, file_path: str, user_id: str):
    raise RuntimeError("Ingestion must be processed by app.worker via Redis queue.")


@router.post("/")
async def upload_and_ingest(
        file: UploadFile = File(...),
        user_id: str = Form(...),
        replace_existing: bool = Form(False),
):
    try:
        # print(f"formdata : {formdata}")
        # file: UploadFile = File(...)
        print(f"user-id :{user_id}")
        validate_pdf_file(file)

        safe_filename = f"{uuid.uuid4()}##{file.filename}"
        file_path = os.path.join(UPLOAD_DIR, safe_filename)

        total_size = 0
        try:
            with open(file_path, "wb") as f:
                while chunk := await file.read(1024 * 1024):
                    total_size += len(chunk)

                    if total_size > MAX_UPLOAD_SIZE_BYTES:
                        raise HTTPException(
                            status_code=413,
                            detail=f"File too large. Maximum allowed size is {MAX_UPLOAD_SIZE_MB} MB."
                        )

                    f.write(chunk)
        except Exception:
            if os.path.exists(file_path):
                os.remove(file_path)
            raise

        validate_file_size(file_path)
        try:
            page_count = validate_pdf_page_count(file_path)
        except Exception:
            if os.path.exists(file_path):
                os.remove(file_path)
            raise
        # detects same file content
        document_hash = calculate_file_hash(file_path)

# Checks:

# Does Postgres know this user already has this file hash?
# Is that document ready?
# Do Qdrant vectors exist for that document/user?

# Why: This prevents showing/returning duplicate based on incomplete metadata.

        existing_document = get_document_by_hash(user_id, document_hash)
        if (
            existing_document
            and existing_document.get("status") == "ready"
            and document_exists(existing_document["document_id"], user_id)
            and not replace_existing
        ):
            os.remove(file_path)

            return {
                "status": "duplicate",
                "message": "This PDF already exists in knowledge base. Send replace_existing=true to re-ingest it safely.",
                "document_id": existing_document["document_id"],
                "document_hash": document_hash,
                "file": file.filename,
                "total_pages": page_count,
                "can_replace": True,
            }
# What it creates:

# user row if missing
# document row if missing
# upload session row
# ingestion job row
# audit event

# Why: Before Redis queue receives the job, Postgres already has durable metadata.

        job_id = str(uuid.uuid4())
        metadata = prepare_upload_metadata(
            external_user_id=user_id,
            document_hash=document_hash,
            original_file_name=file.filename,
            stored_file_name=safe_filename,
            redis_job_id=job_id,
        )

# document_id now comes from Postgres.
# Why: Qdrant vectors should link to Postgres document records.
        document_id = metadata["document_id"]
        upload_session_id = metadata["upload_session_id"]
        previous_active_upload_session_id = metadata.get("previous_active_upload_session_id")

        # # asyncio.create_task(ingest_with_logs(file_path))
        # job_id = str(uuid.uuid4())

        # job_manager.create_job(job_id)

        # asyncio.create_task(
        #     ingest_with_logs(job_id, user_id, file_path)
        # )        

        # # return {
        # #     "status": "accepted",
        # #     "message": "PDF uploaded. Ingestion started.",
        # #     "file": file.filename,
        # #     "document_id": document_id,
        # #     "page_count": page_count,
        # #     "user_id": "default_user",
        # # }
        # return {
        #     "job_id": job_id,
        #     "status": "queued",
        #     "message": "Ingestion started",
        #     "file": file.filename,
        #     "document_id": document_id,
        #     "page_count": page_count
        # }

        # upload_dir = Path("uploads")
        # upload_dir.mkdir(exist_ok=True)

        # file_path = upload_dir / file.filename

        # with open(file_path, "wb") as f:
        #     shutil.copyfileobj(file.file, f)

        if MAX_ACTIVE_JOBS_PER_USER > 0:
            active_jobs = await JobManager.count_active_jobs_for_user(user_id)
            if active_jobs >= MAX_ACTIVE_JOBS_PER_USER:
                if os.path.exists(file_path):
                    os.remove(file_path)

                raise HTTPException(
                    status_code=429,
                    detail=f"Too many active ingestion jobs. Maximum allowed: {MAX_ACTIVE_JOBS_PER_USER}."
                )

# Redis live job status now also knows:

# Postgres document ID
# file hash
# upload session ID

# Why: The frontend can still poll Redis job status, while worker can connect Redis job to Postgres metadata.

        await JobManager.create_job(
            job_id=job_id,
            user_id=user_id,
            file_name=file.filename,
            safe_file_name=safe_filename,
            document_id=document_id,
            document_hash=document_hash,
            upload_session_id=upload_session_id,
        )
# What it does:
# Sends these IDs to the Docker worker.

# Why:

# Worker needs them to:
# update Postgres job/document/session status
# store correct document_id and document_hash in Qdrant payload
        enqueue_job({
            "job_id": job_id,
            "file_name": safe_filename,
            "user_id": user_id,
            "document_id": document_id,
            "document_hash": document_hash,
            "upload_session_id": upload_session_id,
            "previous_active_upload_session_id": previous_active_upload_session_id,
            "replace_existing": replace_existing,
        })        

# Frontend/debugging can see the durable IDs created for this upload.
        return {
            "message": "Upload accepted. Ingestion started.",
            "job_id": job_id,
            "document_id": document_id,
            "document_hash": document_hash,
            "upload_session_id": upload_session_id,
            "file": file.filename,
            "user_id": user_id,
            "replace_existing": replace_existing,
        }

    except HTTPException:
        raise

    except Exception as e:
# What it does:
# If upload fails after saving the file, remove the saved file.

# Why: Prevents orphan files when something fails during metadata/job creation.        
        if "file_path" in locals() and os.path.exists(file_path):
            os.remove(file_path)

        raise HTTPException(
            status_code=500,
            detail=f"Ingestion failed: {str(e)}"
        )

@router.get("/jobs/{job_id}")
async def get_job_status(job_id: str):

    # job = job_manager.get_job(job_id)

    # if not job:
    #     raise HTTPException(status_code=404, detail="Job not found")

    # return {
    #     "job_id": job_id,
    #     "status": job["status"],
    #     "progress": job["progress"],
    #     "current_step": job["current_step"],
    #     "error": job["error"]
    # }

    job = await JobManager.get_job(job_id)

    if not job:
        raise HTTPException(
            status_code=404,
            detail="Job not found"
        )
    return job


# # 🌊 SSE endpoint to stream logs
# @router.get("/stream")
# async def stream_logs():
#     async def event_generator():
#         while True:
#             log = await log_queue.get()
#             yield {"event": "message", "data": log}

#     return EventSourceResponse(event_generator())

# @router.get("/stream/{job_id}")
# async def stream_logs(job_id: str):

#     job = job_manager.get_job(job_id)

#     if not job:
#         raise HTTPException(status_code=404, detail="Job not found")

#     async def event_generator():

#         while True:
#             message = await job["queue"].get()

#             yield {
#                 "event": "message",
#                 "data": message
#             }

#             if job["status"] in ["completed", "failed"]:
#                 break

#     return EventSourceResponse(event_generator())

@router.get("/stream/{job_id}")
async def stream_logs(job_id: str, request: Request):

    async def event_generator():

        pubsub = redis.pubsub()

        # await pubsub.subscribe(f"job:{job_id}")
        await pubsub.subscribe(f"logs:{job_id}")

        try:

            while True:

                if await request.is_disconnected():
                    break

                # message = await pubsub.get_message(
                #     ignore_subscribe_messages=True,
                #     timeout=5
                # )

                message = await pubsub.get_message(
                    ignore_subscribe_messages=True,
                    timeout=5
                )

                if message:
                    yield {
                        "event": "message",
                        "data": message["data"]
                    }

                else:
                    yield {
                        "event": "ping",
                        "data": "keepalive"
                    }

                await asyncio.sleep(0.1)

        finally:
            await pubsub.unsubscribe(f"logs:{job_id}")
            await pubsub.close()

    return EventSourceResponse(event_generator())

