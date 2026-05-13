from fastapi import APIRouter, HTTPException, UploadFile, File
from sse_starlette.sse import EventSourceResponse
import os
import asyncio
import uuid

from app.services.rag_service import ingest_pdf
from app.core.config import UPLOAD_DIR
from app.services.upload_validator import (
    validate_pdf_file,
    validate_file_size,
    validate_pdf_page_count,
    calculate_file_hash,
)
from app.db.qdrant_client import document_exists


router = APIRouter()

os.makedirs(UPLOAD_DIR, exist_ok=True)

log_queue = asyncio.Queue()


# 🔥 Modified ingestion wrapper (push logs)
async def ingest_with_logs(file_path: str):
    loop = asyncio.get_event_loop()

    def log(message: str):
        asyncio.run_coroutine_threadsafe(log_queue.put(message), loop)

    await log_queue.put("✔️ 📥 Ingesting document...")

    result = await loop.run_in_executor(
        None,
        ingest_pdf,
        file_path,
        log
    )

    await log_queue.put("✅ All set! You can start asking questions now.")

    return result


@router.post("/")
async def upload_and_ingest(file: UploadFile = File(...)):
    try:
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

        asyncio.create_task(ingest_with_logs(file_path))

        return {
            "status": "accepted",
            "message": "PDF uploaded. Ingestion started.",
            "file": file.filename,
            "document_id": document_id,
            "page_count": page_count,
            "user_id": "default_user",
        }

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ingestion failed: {str(e)}"
        )
    
# 🌊 SSE endpoint to stream logs
@router.get("/stream")
async def stream_logs():
    async def event_generator():
        while True:
            log = await log_queue.get()
            yield {"event": "message", "data": log}

    return EventSourceResponse(event_generator())