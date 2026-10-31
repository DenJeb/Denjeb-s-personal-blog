"""
========== 当前前台用户中间件 ==========
"""

from starlette.concurrency import run_in_threadpool
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.types import ASGIApp

from app.db import SessionLocal
from app.models import User


def _load_current_user(request: Request) -> User | None:
    user_id = request.session.get("user_id")
    if user_id is None:
        return None

    with SessionLocal() as db:
        user = db.get(User, user_id)
        if (
            user is None
            or not user.is_active
            or request.session.get("user_version") != user.session_version
        ):
            request.session.pop("user_id", None)
            request.session.pop("user_name", None)
            request.session.pop("user_version", None)
            return None
        return user


class CurrentUserMiddleware(BaseHTTPMiddleware):
    """把有效的前台用户挂到 request.state.user，并清理失效会话。"""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        request.state.user = None
        if request.session.get("user_id") is not None:
            request.state.user = await run_in_threadpool(_load_current_user, request)
        return await call_next(request)
