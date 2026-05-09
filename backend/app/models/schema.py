from pydantic import BaseModel
from typing import Optional

class QueryRequest(BaseModel):
    question: str

    document_id: Optional[str] = None
    file_name: Optional[str] = None
    page: Optional[int] = None
    section: Optional[str] = None
    chunk_type: Optional[str] = None
    upload_session_id: Optional[str] = None
    user_id: Optional[str] = "default_user"