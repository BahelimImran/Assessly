from fastapi import APIRouter, UploadFile, File
import os

from app.services.rag_service import ingest_document

router = APIRouter()

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/")
async def upload_and_ingest(file: UploadFile = File(...)):
    try:
        file_path = os.path.join(UPLOAD_DIR, file.filename)

        with open(file_path, "wb") as f:
            f.write(await file.read())

        result = ingest_document(file_path)

        return {
            "message": "Upload + Ingestion successful",
            "file": file.filename,
            "ingestion": result
        }

    except Exception as e:
        return {"error": str(e)}