from dataclasses import dataclass

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.services.auth_service import decode_access_token, get_user_by_external_id


bearer_scheme = HTTPBearer(auto_error=False)


@dataclass
class AuthPrincipal:
    user_id: str
    internal_user_id: str
    role: str

    @property
    def is_guest(self) -> bool:
        return self.role == "guest"

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"


def _principal_from_token(token: str) -> AuthPrincipal:
    payload = decode_access_token(token)
    user_id = payload.get("sub")
    internal_user_id = payload.get("uid")
    role = payload.get("role", "user")

    if not user_id or not internal_user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access token")

    user = get_user_by_external_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or disabled")

    return AuthPrincipal(
        user_id=user["external_id"],
        internal_user_id=user["id"],
        role=user["role"] or role,
    )


async def get_current_principal(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> AuthPrincipal:
    token = credentials.credentials if credentials else request.query_params.get("access_token")
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")

    return _principal_from_token(token)


async def require_user(principal: AuthPrincipal = Depends(get_current_principal)) -> AuthPrincipal:
    if principal.is_guest:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Guest access is not allowed here")
    return principal


async def require_admin(principal: AuthPrincipal = Depends(get_current_principal)) -> AuthPrincipal:
    if not principal.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return principal


async def allow_guest_query_only(principal: AuthPrincipal = Depends(get_current_principal)) -> AuthPrincipal:
    return principal
