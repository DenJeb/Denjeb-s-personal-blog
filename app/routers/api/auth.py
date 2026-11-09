"""
========== 认证 JSON API ==========
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.csrf import (
    clear_csrf_token,
    get_csrf_token,
    rotate_csrf_token,
    verify_csrf_header,
)
from app.deps import DbSession
from app.schemas.auth import (
    CsrfResponse,
    CurrentUser,
    CurrentUserResponse,
    LoginRequest,
    LogoutResponse,
)
from app.services.accounts import LOGIN_WINDOW_SECONDS, authenticate_password

router = APIRouter()


@router.get("/auth/me", response_model=CurrentUserResponse, name="api_me")
def me(request: Request):
    user = getattr(request.state, "user", None)
    return CurrentUserResponse(user=CurrentUser(name=user.username) if user else None)


@router.get("/auth/csrf", response_model=CsrfResponse, name="api_csrf")
def csrf(request: Request):
    return CsrfResponse(csrf_token=get_csrf_token(request))


@router.post("/auth/login", response_model=CurrentUserResponse, name="api_login")
def login(
    payload: LoginRequest,
    request: Request,
    db: DbSession,
    _csrf: None = Depends(verify_csrf_header),
):
    ip = request.client.host if request.client else "unknown"
    result = authenticate_password(db, payload.email, payload.password, ip)

    if result.reason == "blocked":
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=result.message,
            headers={"Retry-After": str(LOGIN_WINDOW_SECONDS)},
        )
    if result.reason == "invalid":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.message,
        )
    if result.reason == "inactive" or result.user is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=result.message or "账号已被禁用，请联系管理员。",
        )

    user = result.user
    request.session["user_id"] = user.id
    request.session["user_name"] = user.username
    request.session["user_version"] = user.session_version
    rotate_csrf_token(request)
    return CurrentUserResponse(user=CurrentUser(name=user.username))


@router.post("/auth/logout", response_model=LogoutResponse, name="api_logout")
def logout(
    request: Request,
    _csrf: None = Depends(verify_csrf_header),
):
    request.session.pop("user_id", None)
    request.session.pop("user_name", None)
    request.session.pop("user_version", None)
    clear_csrf_token(request)
    return LogoutResponse(ok=True)
