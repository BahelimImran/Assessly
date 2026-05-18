import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from fastapi import HTTPException, Response, status
from passlib.context import CryptContext
from sqlalchemy import select

from app.core.config import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    DEMO_USER_ID,
    JWT_ALGORITHM,
    JWT_SECRET_KEY,
    REFRESH_COOKIE_NAME,
    REFRESH_COOKIE_SAMESITE,
    REFRESH_COOKIE_SECURE,
    REFRESH_TOKEN_EXPIRE_DAYS,
)
from app.db.postgres import session_scope
from app.models.metadata_models import RefreshToken, User


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def utc_now():
    return datetime.now(timezone.utc)


def normalize_username(username: str) -> str:
    return username.strip()


# def hash_password(password: str) -> str:
#     return pwd_context.hash(password)

def hash_password(password: str) -> str:
    password = password.strip()

    if len(password.encode("utf-8")) > 72:
        raise HTTPException(
            status_code=400,
            detail="Password must be maximum 72 bytes"
        )

    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str | None) -> bool:
    if not password_hash:
        return False
    return pwd_context.verify(password, password_hash)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def user_to_dict(user: User) -> dict[str, Any]:
    return {
        "id": user.id,
        "external_id": user.external_id,
        "email": user.email,
        "role": user.role,
        "is_active": user.is_active,
    }


def create_access_token(user: dict[str, Any]) -> str:
    now = utc_now()
    payload = {
        "sub": user["external_id"],
        "uid": user["id"],
        "role": user["role"],
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)).timestamp()),
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Access token expired") from exc
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access token") from exc

    if payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")

    return payload


def create_refresh_token(user_id: str) -> str:
    raw_token = secrets.token_urlsafe(48)
    expires_at = utc_now() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    with session_scope() as session:
        session.add(
            RefreshToken(
                user_id=user_id,
                token_hash=hash_token(raw_token),
                expires_at=expires_at,
            )
        )

    return raw_token


def set_refresh_cookie(response: Response, refresh_token: str):
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=refresh_token,
        httponly=True,
        secure=REFRESH_COOKIE_SECURE,
        samesite=REFRESH_COOKIE_SAMESITE,
        max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        path="/auth",
    )


def clear_refresh_cookie(response: Response):
    response.delete_cookie(
        key=REFRESH_COOKIE_NAME,
        path="/auth",
        httponly=True,
        secure=REFRESH_COOKIE_SECURE,
        samesite=REFRESH_COOKIE_SAMESITE,
    )


def register_user(username: str, password: str, email: str | None = None) -> dict[str, Any]:
    external_id = normalize_username(username)
    if len(external_id) < 3:
        raise HTTPException(status_code=400, detail="Username must be at least 3 characters.")
    if len(password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters.")
    if external_id.lower() == normalize_username(DEMO_USER_ID).lower():
        raise HTTPException(status_code=400, detail="This username is reserved.")

    with session_scope() as session:
        existing = session.scalar(select(User).where(User.external_id == external_id))
        if existing:
            if existing.password_hash:
                raise HTTPException(status_code=409, detail="Username already exists.")

            existing.password_hash = hash_password(password)
            existing.email = email.strip().lower() if email else existing.email
            existing.role = "user"
            existing.is_active = 1
            session.flush()
            return user_to_dict(existing)

        user = User(
            external_id=external_id,
            email=email.strip().lower() if email else None,
            password_hash=hash_password(password),
            role="user",
        )
        session.add(user)
        session.flush()
        return user_to_dict(user)


def authenticate_user(username: str, password: str) -> dict[str, Any]:
    external_id = normalize_username(username)

    with session_scope() as session:
        user = session.scalar(select(User).where(User.external_id == external_id))
        if not user or not verify_password(password, user.password_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password.")
        if not user.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is disabled.")

        return user_to_dict(user)


def get_user_by_external_id(external_id: str) -> dict[str, Any] | None:
    with session_scope() as session:
        user = session.scalar(select(User).where(User.external_id == external_id))
        if not user or not user.is_active:
            return None
        return user_to_dict(user)


def get_or_create_guest_user() -> dict[str, Any]:
    external_id = normalize_username(DEMO_USER_ID)

    with session_scope() as session:
        user = session.scalar(select(User).where(User.external_id == external_id))
        if not user:
            user = User(
                external_id=external_id,
                email=None,
                password_hash=None,
                role="guest",
            )
            session.add(user)
            session.flush()
        elif user.role != "guest":
            user.role = "guest"
            session.flush()

        return user_to_dict(user)


def rotate_refresh_token(refresh_token: str) -> tuple[dict[str, Any], str]:
    token_hash = hash_token(refresh_token)
    now = utc_now()

    with session_scope() as session:
        stored_token = session.scalar(
            select(RefreshToken).where(
                RefreshToken.token_hash == token_hash,
                RefreshToken.revoked_at.is_(None),
                RefreshToken.expires_at > now,
            )
        )

        if not stored_token:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token.")

        user = session.get(User, stored_token.user_id)
        if not user or not user.is_active:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token.")

        stored_token.revoked_at = now
        new_refresh_token = secrets.token_urlsafe(48)
        session.add(
            RefreshToken(
                user_id=user.id,
                token_hash=hash_token(new_refresh_token),
                expires_at=now + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
            )
        )
        session.flush()
        return user_to_dict(user), new_refresh_token


def revoke_refresh_token(refresh_token: str | None):
    if not refresh_token:
        return

    token_hash = hash_token(refresh_token)
    with session_scope() as session:
        stored_token = session.scalar(
            select(RefreshToken).where(
                RefreshToken.token_hash == token_hash,
                RefreshToken.revoked_at.is_(None),
            )
        )
        if stored_token:
            stored_token.revoked_at = utc_now()
