from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from sse_starlette.sse import EventSourceResponse
import os
import asyncio
import uuid
from app.services.ingest.job_manager import job_manager

from app.services.rag_service import ingest_pdf
from app.core.config import UPLOAD_DIR
from app.services.upload_validator import (
    validate_pdf_file,
    validate_file_size,
    validate_pdf_page_count,
    calculate_file_hash,
)
from app.db.qdrant_client import document_exists
from app.models.schema import QueryRequest



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

async def ingest_with_logs(job_id: str, user_id: str, file_path: str ):
    loop = asyncio.get_event_loop()

    job_manager.update_status(
        job_id,
        status="processing",
        progress=5,
        current_step="Starting ingestion"
    )
    # Todo : also pass progress number
    def log(message: str):
        asyncio.run_coroutine_threadsafe(
            job_manager.push_log(job_id, message),
            loop
        )

    try:
        await job_manager.push_log(job_id, f"✔️ 📥 Ingesting started...{user_id}")

        result = await loop.run_in_executor(
            None,
            ingest_pdf,
            file_path,
            user_id,
            log
        )

        job_manager.update_status(
            job_id,
            status="completed",
            progress=100,
            current_step="Completed"
        )

        await job_manager.push_log(
            job_id,
            f"✅ All set! You can start asking questions now.{user_id}"
        )

        return result

    except Exception as e:
        job_manager.update_status(
            job_id,
            status="failed",
            error=str(e)
        )

        await job_manager.push_log(
            job_id,
            f"❌ Failed: {str(e)}"
        )


@router.post("/")
async def upload_and_ingest(
        file: UploadFile = File(...),
        user_id: str = Form(...)
):
    try:
        # print(f"formdata : {formdata}")
        # file: UploadFile = File(...)
        print(f"user-id :{user_id}")
        validate_pdf_file(file)

        safe_filename = f"{uuid.uuid4()}##{file.filename}"
        file_path = os.path.join(UPLOAD_DIR, safe_filename)

        with open(file_path, "wb") as f:
            f.write(await file.read())

        validate_file_size(file_path)
        page_count = validate_pdf_page_count(file_path)

        document_id = calculate_file_hash(file_path)

        if document_exists(document_id):
            os.remove(file_path)

            return {
                "status": "duplicate",
                "message": "This PDF already exists in knowledge base.",
                "document_id": document_id,
                "file": file.filename,
            }

        # asyncio.create_task(ingest_with_logs(file_path))
        job_id = str(uuid.uuid4())

        job_manager.create_job(job_id)

        asyncio.create_task(
            ingest_with_logs(job_id, user_id, file_path)
        )        

        # return {
        #     "status": "accepted",
        #     "message": "PDF uploaded. Ingestion started.",
        #     "file": file.filename,
        #     "document_id": document_id,
        #     "page_count": page_count,
        #     "user_id": "default_user",
        # }
        return {
            "job_id": job_id,
            "status": "queued",
            "message": "Ingestion started",
            "file": file.filename,
            "document_id": document_id,
            "page_count": page_count
        }

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ingestion failed: {str(e)}"
        )

@router.get("/jobs/{job_id}")
async def get_job_status(job_id: str):

    job = job_manager.get_job(job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return {
        "job_id": job_id,
        "status": job["status"],
        "progress": job["progress"],
        "current_step": job["current_step"],
        "error": job["error"]
    }


# # 🌊 SSE endpoint to stream logs
# @router.get("/stream")
# async def stream_logs():
#     async def event_generator():
#         while True:
#             log = await log_queue.get()
#             yield {"event": "message", "data": log}

#     return EventSourceResponse(event_generator())

@router.get("/stream/{job_id}")
async def stream_logs(job_id: str):

    job = job_manager.get_job(job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    async def event_generator():

        while True:
            message = await job["queue"].get()

            yield {
                "event": "message",
                "data": message
            }

            if job["status"] in ["completed", "failed"]:
                break

    return EventSourceResponse(event_generator())