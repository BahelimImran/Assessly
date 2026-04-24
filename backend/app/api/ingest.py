from fastapi import APIRouter, HTTPException, UploadFile, File
from sse_starlette.sse import EventSourceResponse
import os
import asyncio

from app.services.rag_service import ingest_pdf

router = APIRouter()

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Shared queue for logs
log_queue = asyncio.Queue()


# 🔥 Modified ingestion wrapper (push logs)
async def ingest_with_logs(file_path: str):
    loop = asyncio.get_event_loop()
    # await log_queue.put("📥 Ingesting document...")
    # await asyncio.sleep(0.5)

    # await log_queue.put("📄 Parsing document structure...")
    # await asyncio.sleep(0.5)

    # await log_queue.put("🧠 Understanding document layout...")
    # await asyncio.sleep(0.5)

    # await log_queue.put("✂️ Splitting into semantic sections...")
    # await asyncio.sleep(0.5)

    # await log_queue.put("🧩 Chunking content...")
    # await asyncio.sleep(0.5)

    # await log_queue.put("🔍 Enriching & validating chunks...")
    # await asyncio.sleep(0.5)

    # await log_queue.put("🧠 Generating embeddings...")
    
    # Call your real function (blocking → run in thread)
    # loop = asyncio.get_event_loop()
    # result = await loop.run_in_executor(None, ingest_pdf, file_path)

    # await log_queue.put("📦 Storing in vector DB...")
    # await asyncio.sleep(0.5)

    def log(message:str):
        asyncio.run_coroutine_threadsafe( log_queue.put(message), loop )

    await log_queue.put("✔️ 📥 Ingesting document...")

    result = await loop.run_in_executor(
        None,
        ingest_pdf,
        file_path,
        log # logger
    )

    await log_queue.put("✅ All set! You can start asking questions now.")

    return result


@router.post("/")
async def upload_and_ingest(file: UploadFile = File(...)):
    try:
        file_path = os.path.join(UPLOAD_DIR, file.filename)

        with open(file_path, "wb") as f:
            f.write(await file.read())

        # result = ingest_pdf(file_path)
        # Run ingestion in background
        asyncio.create_task(ingest_with_logs(file_path))

        return {
            "message": "Upload + Ingestion successful",
            "file": file.filename,
            # "ingestion": result
        }

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