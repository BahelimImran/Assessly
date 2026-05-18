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

class JobStatus(BaseModel):
    job_id: str
    status: str
    progress: int
    current_step: str
    error: Optional[str] = None


class AuthRegisterRequest(BaseModel):
    username: str
    password: str
    email: Optional[str] = None


class AuthLoginRequest(BaseModel):
    username: str
    password: str


class AuthUserResponse(BaseModel):
    user_id: str
    username: str
    email: Optional[str] = None
    role: str


class AuthTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: AuthUserResponse
