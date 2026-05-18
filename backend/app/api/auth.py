from fastapi import APIRouter, Depends, HTTPException, Request, Response

from app.core.config import REFRESH_COOKIE_NAME
from app.models.schema import AuthLoginRequest, AuthRegisterRequest, AuthTokenResponse
from app.services.auth_dependencies import AuthPrincipal, get_current_principal
from app.services.auth_service import (
    authenticate_user,
    clear_refresh_cookie,
    create_access_token,
    create_refresh_token,
    get_or_create_guest_user,
    register_user,
    revoke_refresh_token,
    rotate_refresh_token,
    set_refresh_cookie,
)


router = APIRouter()


def build_auth_response(user: dict, access_token: str) -> dict:
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "user_id": user["external_id"],
            "username": user["external_id"],
            "email": user.get("email"),
            "role": user["role"],
        },
    }


@router.post("/register", response_model=AuthTokenResponse)
def register(payload: AuthRegisterRequest, response: Response):
    user = register_user(payload.username, payload.password, payload.email)
    refresh_token = create_refresh_token(user["id"])
    set_refresh_cookie(response, refresh_token)
    return build_auth_response(user, create_access_token(user))


@router.post("/login", response_model=AuthTokenResponse)
def login(payload: AuthLoginRequest, response: Response):
    user = authenticate_user(payload.username, payload.password)
    refresh_token = create_refresh_token(user["id"])
    set_refresh_cookie(response, refresh_token)
    return build_auth_response(user, create_access_token(user))


@router.post("/guest", response_model=AuthTokenResponse)
def guest_login(response: Response):
    clear_refresh_cookie(response)
    user = get_or_create_guest_user()
    return build_auth_response(user, create_access_token(user))


@router.post("/refresh", response_model=AuthTokenResponse)
def refresh(request: Request, response: Response):
    refresh_token = request.cookies.get(REFRESH_COOKIE_NAME)
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Refresh token required")

    user, new_refresh_token = rotate_refresh_token(refresh_token)
    set_refresh_cookie(response, new_refresh_token)
    return build_auth_response(user, create_access_token(user))


@router.post("/logout")
def logout(request: Request, response: Response):
    revoke_refresh_token(request.cookies.get(REFRESH_COOKIE_NAME))
    clear_refresh_cookie(response)
    return {"status": "logged_out"}


@router.get("/me")
def me(principal: AuthPrincipal = Depends(get_current_principal)):
    return {
        "user_id": principal.user_id,
        "username": principal.user_id,
        "role": principal.role,
    }
