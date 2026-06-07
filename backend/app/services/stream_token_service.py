import secrets

from app.core.config import STREAM_TOKEN_TTL_SECONDS
from app.services.redis_client import redis_client


def _stream_token_key(purpose: str, job_id: str, token: str) -> str:
    return f"stream_token:{purpose}:{job_id}:{token}"


def create_stream_token(*, purpose: str, job_id: str, user_id: str) -> str:
    token = secrets.token_urlsafe(32)
    redis_client.setex(
        _stream_token_key(purpose, job_id, token),
        STREAM_TOKEN_TTL_SECONDS,
        user_id,
    )
    return token


def validate_stream_token(*, purpose: str, job_id: str, token: str | None) -> str | None:
    if not token:
        return None

    key = _stream_token_key(purpose, job_id, token)
    user_id = redis_client.get(key)
    if not user_id:
        return None

    return user_id
