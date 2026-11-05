"""
========== 后台登录与退出 ==========
"""

from datetime import UTC, datetime

import pyotp
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
from app.services.accounts import (
    PURPOSE_ADMIN_LOGIN,
    code_matches,
    load_pending_code,
    record_failed_code_attempt,
    send_verification_code,
)
from app.templating import templates

router = APIRouter()
password_hash = PasswordHash.recommended()

LOGIN_WINDOW_SECONDS = 300
LOGIN_MAX_FAILURES = 5
PENDING_TTL_SECONDS = 300
PENDING_ADMIN_ID = "pending_admin_id"
PENDING_ADMIN_VERSION = "pending_admin_version"
PENDING_ADMIN_AT = "pending_admin_at"
PENDING_CODE = "pending_admin_login_code"
CODE_SEND_WINDOW_SECONDS = 600
CODE_SEND_MAX = 5


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


def _code_bucket(ip: str) -> str:
    return f"admin_login_code:{ip}"


def _code_is_blocked(db: Session, ip: str) -> bool:
    return is_rate_limited(
        db, _code_bucket(ip), CODE_SEND_WINDOW_SECONDS, CODE_SEND_MAX
    )


def _record_code_send(db: Session, ip: str) -> None:
    record_event(db, _code_bucket(ip))


def _clear_pending_code(request: Request) -> None:
    request.session.pop(PENDING_CODE, None)


def _pending_code(request: Request, db: Session):
    pending = request.session.get(PENDING_CODE)
    if not pending:
        return None, None

    row = load_pending_code(db, pending, PURPOSE_ADMIN_LOGIN)
    if row is None:
        _clear_pending_code(request)
        return None, None
    return pending, row


def _admin_for_pending_code(db: Session, pending: dict | None) -> AdminUser | None:
    if not pending or not pending.get("email"):
        return None

    admin = db.scalar(select(AdminUser).where(AdminUser.email == pending["email"]))
    if (
        admin is None
        or (admin.email or "").lower() != settings.admin_email_normalized
        or pending.get("admin_version") != admin.session_version
    ):
        return None
    return admin


def _code_email_bucket(email: str) -> str:
    return f"admin_login_code_email:{email.strip().lower()}"


def _code_email_is_blocked(db: Session, email: str) -> bool:
    return is_rate_limited(
        db, _code_email_bucket(email), CODE_SEND_WINDOW_SECONDS, CODE_SEND_MAX
    )


def _record_code_email_send(db: Session, email: str) -> None:
    record_event(db, _code_email_bucket(email))


def _login_page(
    request: Request,
    username: str = "",
    error: str | None = None,
    status_code: int = 200,
    headers: dict[str, str] | None = None,
):
    return templates.TemplateResponse(
        request=request,
        name="admin/login.html",
        context={
            "app_name": settings.app_name,
            "username": username,
            "error": error,
            "code_enabled": settings.admin_login_code_enabled,
        },
        status_code=status_code,
        headers=headers,
    )


def _code_page(
    request: Request,
    email: str | None,
    error: str | None = None,
    sent: bool = False,
    status_code: int = 200,
    headers: dict[str, str] | None = None,
):
    return templates.TemplateResponse(
        request=request,
        name="admin/login_code.html",
        context={
            "app_name": settings.app_name,
            "email": email,
            "error": error,
            "sent": sent,
        },
        status_code=status_code,
        headers=headers,
    )


def _finish_login(
    request: Request, db: Session, admin: AdminUser, ip: str
) -> RedirectResponse:
    if admin.totp_secret:
        request.session.pop("admin_user_id", None)
        request.session.pop("admin_version", None)
        request.session[PENDING_ADMIN_ID] = admin.id
        request.session[PENDING_ADMIN_VERSION] = admin.session_version
        request.session[PENDING_ADMIN_AT] = datetime.now(UTC).timestamp()
        return RedirectResponse("/admin/login/totp", status_code=303)

    clear_bucket(db, _login_bucket(ip))
    request.session["admin_user_id"] = admin.id
    request.session["admin_version"] = admin.session_version
    return RedirectResponse("/admin/", status_code=303)


def _clear_pending(request: Request) -> None:
    request.session.pop(PENDING_ADMIN_ID, None)
    request.session.pop(PENDING_ADMIN_VERSION, None)
    request.session.pop(PENDING_ADMIN_AT, None)


def _pending_admin(request: Request, db: Session) -> AdminUser | None:
    admin_id = request.session.get(PENDING_ADMIN_ID)
    timestamp = request.session.get(PENDING_ADMIN_AT)
    if admin_id is None or timestamp is None:
        return None
    if datetime.now(UTC).timestamp() - float(timestamp) > PENDING_TTL_SECONDS:
        _clear_pending(request)
        return None

    admin = db.get(AdminUser, admin_id)
    if (
        admin is None
        or not admin.totp_secret
        or (admin.email or "").lower() != settings.admin_email_normalized
        or request.session.get(PENDING_ADMIN_VERSION) != admin.session_version
    ):
        _clear_pending(request)
        return None
    return admin


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

    if settings.admin_login_code_enabled:
        pending, _ = _pending_code(request, db)
        if pending is not None:
            return RedirectResponse("/admin/login/code", status_code=303)

    if _pending_admin(request, db) is not None:
        return RedirectResponse("/admin/login/totp", status_code=303)

    return _login_page(request)


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
        return _login_page(
            request,
            username,
            "尝试次数过多，请 5 分钟后再试。",
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
        return _login_page(
            request,
            username,
            "管理员邮箱或密码错误",
            status_code=400,
        )

    if settings.admin_login_code_enabled:
        email = (user.email or settings.admin_email_normalized).strip().lower()
        if _code_is_blocked(db, ip) or _code_email_is_blocked(db, email):
            return _login_page(
                request,
                username,
                "验证码请求过于频繁，请稍后再试。",
                status_code=429,
                headers={"Retry-After": str(CODE_SEND_WINDOW_SECONDS)},
            )

        _clear_pending_code(request)
        _clear_pending(request)
        _record_code_send(db, ip)
        _record_code_email_send(db, email)
        row = send_verification_code(db, email, PURPOSE_ADMIN_LOGIN)
        if row is None:
            if user.totp_secret:
                return _finish_login(request, db, user, ip)
            return _login_page(
                request,
                username,
                "验证码发送失败，请检查 SMTP；"
                "也可在服务器设置 ADMIN_LOGIN_CODE_ENABLED=false 后重启登录。",
                status_code=503,
            )

        request.session.pop("admin_user_id", None)
        request.session.pop("admin_version", None)
        _clear_pending(request)
        request.session[PENDING_CODE] = {
            "code_id": row.id,
            "email": email,
            "admin_version": user.session_version,
        }
        return RedirectResponse("/admin/login/code", status_code=303)

    return _finish_login(request, db, user, ip)


@router.get("/login/code")
def login_code_page(request: Request, db: DbSession):
    if not settings.admin_login_code_enabled:
        return RedirectResponse("/admin/login", status_code=303)

    pending, _ = _pending_code(request, db)
    if pending is None:
        return RedirectResponse("/admin/login", status_code=303)

    return _code_page(
        request,
        pending.get("email"),
        sent=request.query_params.get("sent") == "1",
    )


@router.post("/login/code")
def login_code_verify(
    request: Request,
    db: DbSession,
    code: str = Form(...),
    _csrf: None = Depends(verify_csrf),
):
    if not settings.admin_login_code_enabled:
        return RedirectResponse("/admin/login", status_code=303)

    pending, row = _pending_code(request, db)
    if pending is None or row is None:
        return RedirectResponse("/admin/login", status_code=303)

    admin = _admin_for_pending_code(db, pending)
    if admin is None:
        db.delete(row)
        db.commit()
        _clear_pending_code(request)
        return RedirectResponse("/admin/login", status_code=303)

    if not code_matches(row, code):
        if record_failed_code_attempt(db, row):
            _clear_pending_code(request)
            return RedirectResponse("/admin/login", status_code=303)
        return _code_page(
            request,
            pending.get("email"),
            "验证码不正确，请重试。",
            status_code=400,
        )

    db.delete(row)
    db.commit()
    _clear_pending_code(request)
    ip = _client_ip(request)
    clear_bucket(db, _code_bucket(ip))
    clear_bucket(db, _code_email_bucket(admin.email or pending.get("email", "")))
    return _finish_login(request, db, admin, ip)


@router.post("/login/code/resend")
def login_code_resend(
    request: Request,
    db: DbSession,
    _csrf: None = Depends(verify_csrf),
):
    if not settings.admin_login_code_enabled:
        return RedirectResponse("/admin/login", status_code=303)

    pending, row = _pending_code(request, db)
    if pending is None or row is None:
        return RedirectResponse("/admin/login", status_code=303)

    admin = _admin_for_pending_code(db, pending)
    if admin is None:
        db.delete(row)
        db.commit()
        _clear_pending_code(request)
        return RedirectResponse("/admin/login", status_code=303)

    email = (admin.email or settings.admin_email_normalized).strip().lower()
    ip = _client_ip(request)
    if _code_is_blocked(db, ip) or _code_email_is_blocked(db, email):
        return _code_page(
            request,
            email,
            "验证码请求过于频繁，请稍后再试。",
            status_code=429,
            headers={"Retry-After": str(CODE_SEND_WINDOW_SECONDS)},
        )

    _record_code_send(db, ip)
    _record_code_email_send(db, email)
    row = send_verification_code(db, email, PURPOSE_ADMIN_LOGIN)
    if row is None:
        return _code_page(
            request,
            email,
            "验证码发送失败，请检查 SMTP 配置或稍后再试。",
            status_code=503,
        )

    request.session[PENDING_CODE] = {
        "code_id": row.id,
        "email": email,
        "admin_version": admin.session_version,
    }
    return RedirectResponse("/admin/login/code?sent=1", status_code=303)


@router.post("/login/code/cancel")
def login_code_cancel(
    request: Request,
    db: DbSession,
    _csrf: None = Depends(verify_csrf),
):
    _, row = _pending_code(request, db)
    if row is not None:
        db.delete(row)
        db.commit()
    _clear_pending_code(request)
    _clear_pending(request)
    return RedirectResponse("/admin/login", status_code=303)


@router.get("/login/totp")
def login_totp_page(request: Request, db: DbSession):
    admin = _pending_admin(request, db)
    if admin is None:
        return RedirectResponse("/admin/login", status_code=303)
    return templates.TemplateResponse(
        request=request,
        name="admin/login_totp.html",
        context={"app_name": settings.app_name, "email": admin.email},
    )


@router.post("/login/totp")
def login_totp(
    request: Request,
    db: DbSession,
    code: str = Form(...),
    _csrf: None = Depends(verify_csrf),
):
    ip = _client_ip(request)
    if _login_is_blocked(db, ip):
        return templates.TemplateResponse(
            request=request,
            name="admin/login_totp.html",
            context={
                "app_name": settings.app_name,
                "error": "尝试次数过多，请 5 分钟后再试。",
            },
            status_code=429,
            headers={"Retry-After": str(LOGIN_WINDOW_SECONDS)},
        )

    admin = _pending_admin(request, db)
    if admin is None:
        return RedirectResponse("/admin/login", status_code=303)

    if not pyotp.TOTP(admin.totp_secret).verify(code.strip(), valid_window=1):
        _record_login_failure(db, ip)
        return templates.TemplateResponse(
            request=request,
            name="admin/login_totp.html",
            context={
                "app_name": settings.app_name,
                "email": admin.email,
                "error": "验证码不正确，请重试。",
            },
            status_code=400,
        )

    clear_bucket(db, _login_bucket(ip))
    _clear_pending(request)
    _clear_pending_code(request)
    request.session["admin_user_id"] = admin.id
    request.session["admin_version"] = admin.session_version
    return RedirectResponse("/admin/", status_code=303)


@router.post("/logout")
def logout(request: Request, _csrf: None = Depends(verify_csrf)):
    request.session.pop("admin_user_id", None)
    request.session.pop("admin_version", None)
    _clear_pending(request)
    _clear_pending_code(request)
    return RedirectResponse("/admin/login", status_code=303)
