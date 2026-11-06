"""
========== 认证 JSON API ==========
"""

from fastapi import APIRouter, Request

from app.schemas.auth import CurrentUser, CurrentUserResponse

router = APIRouter()


@router.get("/auth/me", response_model=CurrentUserResponse)
def me(request: Request):
    user = getattr(request.state, "user", None)
    return CurrentUserResponse(user=CurrentUser(name=user.username) if user else None)
