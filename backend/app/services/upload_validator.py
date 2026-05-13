import os
import hashlib
from pathlib import Path
from fastapi import HTTPException, UploadFile
from pypdf import PdfReader

from app.core.config import MAX_UPLOAD_SIZE_BYTES, MAX_UPLOAD_SIZE_MB, MAX_PDF_PAGES


def is_pdf(file: UploadFile) -> bool:
    filename = file.filename or ""
    content_type = file.content_type or ""

    return (
        filename.lower().endswith(".pdf")
        and content_type in ["application/pdf", "application/octet-stream"]
    )


def calculate_file_hash(file_path: str) -> str:
    sha256 = hashlib.sha256()

    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            sha256.update(chunk)

    return sha256.hexdigest()


def validate_pdf_file(file: UploadFile):
    if not is_pdf(file):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are allowed."
        )


def validate_file_size(file_path: str):
    size = os.path.getsize(file_path)

    if size > MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum allowed size is {MAX_UPLOAD_SIZE_MB} MB."
        )


def validate_pdf_page_count(file_path: str):
    try:
        reader = PdfReader(file_path)
        page_count = len(reader.pages)

        if page_count > MAX_PDF_PAGES:
            raise HTTPException(
                status_code=400,
                detail=f"PDF has {page_count} pages. Maximum allowed pages: {MAX_PDF_PAGES}."
            )

        return page_count

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Invalid or corrupted PDF file."
        )