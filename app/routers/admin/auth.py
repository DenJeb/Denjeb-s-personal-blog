"""
========== 后台登录与退出 ==========
"""

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from pwdlib import PasswordHash
from pwdlib.exceptions import UnknownHashError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.csrf import verify_csrf
from app.deps import DbSession
from app.models import AdminUser
from app.rate_limit import clear_bucket, is_rate_limited, record_event
from app.templating import templates

router = APIRouter()
password_hash = PasswordHash.recommended()

LOGIN_WINDOW_SECONDS = 300
LOGIN_MAX_FAILURES = 5


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _login_bucket(ip: str) -> str:
    return f"admin_login:{ip}"


def _login_is_blocked(db: Session, ip: str) -> bool:
    return is_rate_limited(
        db, _login_bucket(ip), LOGIN_WINDOW_SECONDS, LOGIN_MAX_FAILURES
    )


def _record_login_failure(db: Session, ip: str) -> None:
    record_event(db, _login_bucket(ip))


@router.get("/login")
def login_page(request: Request, db: DbSession):
    admin_id = request.session.get("admin_user_id")
    if admin_id is not None:
        admin = db.get(AdminUser, admin_id)
        if (
            admin is not None
            and (admin.email or "").lower() == settings.admin_email_normalized
            and request.session.get("admin_version") == admin.session_version
        ):
            return RedirectResponse("/admin/", status_code=303)
        request.session.pop("admin_user_id", None)
        request.session.pop("admin_version", None)

    return templates.TemplateResponse(
        request=request,
        name="admin/login.html",
        context={"app_name": settings.app_name},
    )


@router.post("/login")
def login(
    request: Request,
    db: DbSession,
    username: str = Form(...),
    password: str = Form(...),
    _csrf: None = Depends(verify_csrf),
):
    ip = _client_ip(request)
    if _login_is_blocked(db, ip):
        return templates.TemplateResponse(
            request=request,
            name="admin/login.html",
            context={
                "app_name": settings.app_name,
                "error": "尝试次数过多，请 5 分钟后再试。",
                "username": username,
            },
            status_code=429,
            headers={"Retry-After": str(LOGIN_WINDOW_SECONDS)},
        )

    account = username.strip().lower()
    user = None
    if account == settings.admin_email_normalized:
        user = db.scalar(
            select(AdminUser).where(AdminUser.email == settings.admin_email_normalized)
        )

    valid = False
    if user is not None:
        try:
            valid = password_hash.verify(password, user.password_hash)
        except UnknownHashError:
            valid = False

    if user is None or not valid:
        _record_login_failure(db, ip)
        return templates.TemplateResponse(
            request=request,
            name="admin/login.html",
            context={
                "app_name": settings.app_name,
                "error": "管理员邮箱或密码错误",
                "username": username,
            },
            status_code=400,
        )

    clear_bucket(db, _login_bucket(ip))
    request.session["admin_user_id"] = user.id
    request.session["admin_version"] = user.session_version
    return RedirectResponse("/admin/", status_code=303)


@router.post("/logout")
def logout(request: Request, _csrf: None = Depends(verify_csrf)):
    request.session.pop("admin_user_id", None)
    request.session.pop("admin_version", None)
    return RedirectResponse("/admin/login", status_code=303)
