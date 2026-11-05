"""
========== 前台账号：邮箱注册、验证码、登录、密码重置 ==========
"""

import re
from datetime import timedelta

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from pwdlib import PasswordHash
from pwdlib.exceptions import UnknownHashError
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.csrf import verify_csrf
from app.deps import DbSession
from app.models import EmailRegistrationBlock, User, VerificationCode
from app.rate_limit import clear_bucket, is_rate_limited, record_event
from app.services.accounts import (
    EMAIL_BLOCK_HOURS,
    PURPOSE_LOGIN_CODE,
    PURPOSE_REGISTER,
    PURPOSE_RESET,
    code_matches,
    load_pending_code,
    now_naive,
    record_failed_code_attempt,
    registration_is_blocked,
    safe_next,
    send_verification_code,
    valid_nickname,
)
from app.templating import templates

router = APIRouter()
password_hash = PasswordHash.recommended()

LOGIN_WINDOW_SECONDS = 300
LOGIN_MAX_FAILURES = 5
REGISTER_WINDOW_SECONDS = 3600
REGISTER_MAX = 3
RESET_WINDOW_SECONDS = 3600
RESET_MAX = 3
LOGIN_CODE_WINDOW_SECONDS = 600
LOGIN_CODE_MAX = 5
REGISTER_PROBE_MAX = 30
LOGIN_CODE_PROBE_MAX = 30

SESSION_REGISTER = "pending_registration"
SESSION_LOGIN_CODE = "pending_login_code"
SESSION_RESET = "pending_reset"

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _login_bucket(ip: str) -> str:
    return f"user_login:{ip}"


def _login_is_blocked(db: Session, ip: str) -> bool:
    return is_rate_limited(
        db, _login_bucket(ip), LOGIN_WINDOW_SECONDS, LOGIN_MAX_FAILURES
    )


def _record_login_failure(db: Session, ip: str) -> None:
    record_event(db, _login_bucket(ip))


def _register_is_blocked(db: Session, ip: str) -> bool:
    return is_rate_limited(db, f"register:{ip}", REGISTER_WINDOW_SECONDS, REGISTER_MAX)


def _record_registration(db: Session, ip: str) -> None:
    record_event(db, f"register:{ip}")


def _reset_is_blocked(db: Session, ip: str) -> bool:
    return is_rate_limited(db, f"reset:{ip}", RESET_WINDOW_SECONDS, RESET_MAX)


def _record_reset(db: Session, ip: str) -> None:
    record_event(db, f"reset:{ip}")


def _login_code_is_blocked(db: Session, ip: str) -> bool:
    return is_rate_limited(
        db, f"login_code:{ip}", LOGIN_CODE_WINDOW_SECONDS, LOGIN_CODE_MAX
    )


def _record_login_code(db: Session, ip: str) -> None:
    record_event(db, f"login_code:{ip}")


def _email_code_is_blocked(
    db: Session,
    purpose: str,
    email: str,
    window_seconds: int,
    max_events: int,
) -> bool:
    return is_rate_limited(db, f"{purpose}_email:{email}", window_seconds, max_events)


def _record_email_code(db: Session, purpose: str, email: str) -> None:
    record_event(db, f"{purpose}_email:{email}")


@router.get("/register")
def user_register_page(request: Request, next: str = ""):
    if getattr(request.state, "user", None) is not None:
        return RedirectResponse("/", status_code=303)
    return templates.TemplateResponse(
        request=request,
        name="account/register.html",
        context={
            "app_name": settings.app_name,
            "next": safe_next(next),
        },
    )


@router.post("/register")
def user_register(
    request: Request,
    db: DbSession,
    email: str = Form(..., max_length=255),
    nickname: str = Form(..., max_length=30),
    password: str = Form(...),
    confirm: str = Form(...),
    next: str = Form(""),
    website: str = Form(""),
    _csrf: None = Depends(verify_csrf),
):
    email = email.strip().lower()
    nickname = nickname.strip()

    if website.strip():
        return RedirectResponse("/", status_code=303)

    ip = _client_ip(request)
    if is_rate_limited(
        db,
        f"register_probe:{ip}",
        REGISTER_WINDOW_SECONDS,
        REGISTER_PROBE_MAX,
    ):
        return templates.TemplateResponse(
            request=request,
            name="account/register.html",
            context={
                "app_name": settings.app_name,
                "error": "请求过于频繁，请稍后再试。",
                "email": email,
                "nickname": nickname,
                "next": safe_next(next),
            },
            status_code=429,
            headers={"Retry-After": str(REGISTER_WINDOW_SECONDS)},
        )
    record_event(db, f"register_probe:{ip}")

    error = None
    if EMAIL_RE.fullmatch(email) is None:
        error = "邮箱格式不正确。"
    elif not valid_nickname(nickname):
        error = "昵称需为 3-30 个字符，只能包含字母、数字、下划线或中文。"
    elif len(password) < 8:
        error = "密码至少 8 位。"
    elif password != confirm:
        error = "两次密码不一致。"
    elif db.scalar(select(User.id).where(User.email == email)) is not None:
        error = "邮箱已被使用。"
    elif db.scalar(select(User.id).where(User.username == nickname)) is not None:
        error = "昵称已被使用。"
    elif registration_is_blocked(db, email):
        error = "该邮箱注销后 24 小时内不能重新注册。"

    if error is None and _register_is_blocked(db, ip):
        error = "注册过于频繁，请稍后再试。"

    if error is not None:
        return templates.TemplateResponse(
            request=request,
            name="account/register.html",
            context={
                "app_name": settings.app_name,
                "error": error,
                "email": email,
                "nickname": nickname,
                "next": safe_next(next),
            },
            status_code=400,
        )

    if _email_code_is_blocked(
        db,
        PURPOSE_REGISTER,
        email,
        REGISTER_WINDOW_SECONDS,
        REGISTER_MAX,
    ):
        return templates.TemplateResponse(
            request=request,
            name="account/register.html",
            context={
                "app_name": settings.app_name,
                "error": "该邮箱请求验证码过于频繁，请稍后再试。",
                "email": email,
                "nickname": nickname,
                "next": safe_next(next),
            },
            status_code=429,
            headers={"Retry-After": str(REGISTER_WINDOW_SECONDS)},
        )

    row = send_verification_code(
        db,
        email,
        PURPOSE_REGISTER,
        payload={
            "nickname": nickname,
            "password_hash": password_hash.hash(password),
        },
    )
    if row is None:
        request.session.pop(SESSION_REGISTER, None)
        return templates.TemplateResponse(
            request=request,
            name="account/register.html",
            context={
                "app_name": settings.app_name,
                "error": "验证码发送失败，请检查 SMTP 配置或稍后再试。",
                "email": email,
                "nickname": nickname,
                "next": safe_next(next),
            },
            status_code=503,
        )

    request.session[SESSION_REGISTER] = {
        "code_id": row.id,
        "email": email,
        "resends": 0,
        "next": safe_next(next),
    }
    _record_email_code(db, PURPOSE_REGISTER, email)
    _record_registration(db, ip)
    return RedirectResponse("/register/verify", status_code=303)


@router.get("/register/verify")
def user_register_verify_page(request: Request, db: DbSession):
    pending = request.session.get(SESSION_REGISTER)
    if pending is None:
        return RedirectResponse("/register", status_code=303)

    if load_pending_code(db, pending, PURPOSE_REGISTER) is None:
        request.session.pop(SESSION_REGISTER, None)
        return RedirectResponse("/register", status_code=303)

    return templates.TemplateResponse(
        request=request,
        name="account/verify.html",
        context={
            "app_name": settings.app_name,
            "email": pending["email"],
        },
    )


@router.post("/register/verify")
def user_register_verify(
    request: Request,
    db: DbSession,
    code: str = Form(...),
    _csrf: None = Depends(verify_csrf),
):
    pending = request.session.get(SESSION_REGISTER)
    if pending is None:
        return RedirectResponse("/register", status_code=303)

    row = load_pending_code(db, pending, PURPOSE_REGISTER)
    if row is None:
        request.session.pop(SESSION_REGISTER, None)
        return RedirectResponse("/register", status_code=303)

    if not code_matches(row, code):
        if record_failed_code_attempt(db, row):
            request.session.pop(SESSION_REGISTER, None)
            return RedirectResponse("/register", status_code=303)

        return templates.TemplateResponse(
            request=request,
            name="account/verify.html",
            context={
                "app_name": settings.app_name,
                "email": pending["email"],
                "error": "验证码错误，请重试。",
            },
            status_code=400,
        )

    payload = row.payload or {}
    email = pending["email"]
    nickname = payload.get("nickname")
    pending_password_hash = payload.get("password_hash")
    if not nickname or not pending_password_hash:
        db.delete(row)
        db.commit()
        request.session.pop(SESSION_REGISTER, None)
        return RedirectResponse("/register", status_code=303)

    if (
        registration_is_blocked(db, email)
        or db.scalar(select(User.id).where(User.email == email)) is not None
        or db.scalar(select(User.id).where(User.username == nickname)) is not None
    ):
        db.delete(row)
        db.commit()
        request.session.pop(SESSION_REGISTER, None)
        return templates.TemplateResponse(
            request=request,
            name="account/register.html",
            context={
                "app_name": settings.app_name,
                "error": "邮箱或昵称已被使用，请重新注册。",
                "email": email,
                "nickname": nickname,
                "next": pending.get("next", "/"),
            },
            status_code=400,
        )

    db.delete(row)
    db.commit()
    request.session.pop(SESSION_REGISTER, None)

    user = User(
        email=email,
        username=nickname,
        password_hash=pending_password_hash,
    )
    try:
        db.add(user)
        db.commit()
    except IntegrityError:
        db.rollback()
        return templates.TemplateResponse(
            request=request,
            name="account/register.html",
            context={
                "app_name": settings.app_name,
                "error": "邮箱或昵称已被使用，请重新注册。",
                "email": email,
                "nickname": nickname,
                "next": pending.get("next", "/"),
            },
            status_code=400,
        )

    request.session["user_id"] = user.id
    request.session["user_name"] = user.username
    request.session["user_version"] = user.session_version
    return RedirectResponse(pending.get("next", "/"), status_code=303)


@router.post("/register/resend")
def user_register_resend(
    request: Request,
    db: DbSession,
    _csrf: None = Depends(verify_csrf),
):
    pending = request.session.get(SESSION_REGISTER)
    if pending is None:
        return RedirectResponse("/register", status_code=303)

    row = load_pending_code(db, pending, PURPOSE_REGISTER)
    if row is None:
        request.session.pop(SESSION_REGISTER, None)
        return RedirectResponse("/register", status_code=303)

    if pending.get("resends", 0) >= 3:
        return templates.TemplateResponse(
            request=request,
            name="account/verify.html",
            context={
                "app_name": settings.app_name,
                "email": pending["email"],
                "error": "重发次数过多，请重新注册。",
            },
            status_code=400,
        )

    new_row = send_verification_code(
        db,
        row.email,
        PURPOSE_REGISTER,
        payload=row.payload,
    )
    if new_row is None:
        return templates.TemplateResponse(
            request=request,
            name="account/verify.html",
            context={
                "app_name": settings.app_name,
                "email": pending["email"],
                "error": "验证码发送失败，请检查 SMTP 配置或稍后再试。",
            },
            status_code=503,
        )

    pending["code_id"] = new_row.id
    pending["resends"] = pending.get("resends", 0) + 1
    request.session[SESSION_REGISTER] = pending
    return RedirectResponse("/register/verify?resent=1", status_code=303)


@router.get("/forgot-password")
def user_forgot_password_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="account/forgot_password.html",
        context={"app_name": settings.app_name},
    )


@router.post("/forgot-password")
def user_forgot_password(
    request: Request,
    db: DbSession,
    email: str = Form(...),
    _csrf: None = Depends(verify_csrf),
):
    email = email.strip().lower()
    if EMAIL_RE.fullmatch(email) is None:
        return templates.TemplateResponse(
            request=request,
            name="account/forgot_password.html",
            context={
                "app_name": settings.app_name,
                "error": "邮箱格式不正确。",
                "email": email,
            },
            status_code=400,
        )

    ip = _client_ip(request)
    if _reset_is_blocked(db, ip):
        return templates.TemplateResponse(
            request=request,
            name="account/forgot_password.html",
            context={
                "app_name": settings.app_name,
                "error": "请求过于频繁，请稍后再试。",
                "email": email,
            },
            status_code=429,
        )

    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        request.session[SESSION_RESET] = {"code_id": None, "email": email}
        _record_reset(db, ip)
        return RedirectResponse("/reset-password", status_code=303)

    if _email_code_is_blocked(
        db,
        PURPOSE_RESET,
        email,
        RESET_WINDOW_SECONDS,
        RESET_MAX,
    ):
        return templates.TemplateResponse(
            request=request,
            name="account/forgot_password.html",
            context={
                "app_name": settings.app_name,
                "error": "该邮箱请求验证码过于频繁，请稍后再试。",
                "email": email,
            },
            status_code=429,
        )

    row = send_verification_code(db, email, PURPOSE_RESET)
    if row is None:
        request.session.pop(SESSION_RESET, None)
        return templates.TemplateResponse(
            request=request,
            name="account/forgot_password.html",
            context={
                "app_name": settings.app_name,
                "error": "验证码发送失败，请检查 SMTP 配置或稍后再试。",
                "email": email,
            },
            status_code=503,
        )

    request.session[SESSION_RESET] = {"code_id": row.id, "email": email}
    _record_email_code(db, PURPOSE_RESET, email)
    _record_reset(db, ip)
    return RedirectResponse("/reset-password", status_code=303)


@router.get("/reset-password")
def user_reset_password_page(request: Request):
    pending = request.session.get(SESSION_RESET)
    if pending is None:
        return RedirectResponse("/forgot-password", status_code=303)
    return templates.TemplateResponse(
        request=request,
        name="account/reset_password.html",
        context={
            "app_name": settings.app_name,
            "email": pending["email"],
        },
    )


@router.post("/reset-password")
def user_reset_password(
    request: Request,
    db: DbSession,
    code: str = Form(...),
    password: str = Form(...),
    confirm: str = Form(...),
    _csrf: None = Depends(verify_csrf),
):
    pending = request.session.get(SESSION_RESET)
    if pending is None:
        return RedirectResponse("/forgot-password", status_code=303)

    row = load_pending_code(db, pending, PURPOSE_RESET)
    if row is None:
        request.session.pop(SESSION_RESET, None)
        return RedirectResponse("/forgot-password", status_code=303)

    if not code_matches(row, code):
        if record_failed_code_attempt(db, row):
            request.session.pop(SESSION_RESET, None)
            return RedirectResponse("/forgot-password", status_code=303)

        return templates.TemplateResponse(
            request=request,
            name="account/reset_password.html",
            context={
                "app_name": settings.app_name,
                "email": pending["email"],
                "error": "验证码错误，请重试。",
            },
            status_code=400,
        )

    if len(password) < 8:
        error = "密码至少 8 位。"
    elif password != confirm:
        error = "两次密码不一致。"
    else:
        error = None

    if error is not None:
        return templates.TemplateResponse(
            request=request,
            name="account/reset_password.html",
            context={
                "app_name": settings.app_name,
                "email": pending["email"],
                "error": error,
            },
            status_code=400,
        )

    user = db.scalar(select(User).where(User.email == pending["email"]))
    if user is None:
        db.delete(row)
        db.commit()
        request.session.pop(SESSION_RESET, None)
        return templates.TemplateResponse(
            request=request,
            name="account/forgot_password.html",
            context={
                "app_name": settings.app_name,
                "error": "账号不存在或已删除。",
            },
            status_code=400,
        )

    user.password_hash = password_hash.hash(password)
    user.session_version += 1
    db.execute(
        delete(VerificationCode).where(VerificationCode.email == pending["email"])
    )
    db.commit()
    request.session.pop(SESSION_RESET, None)
    return RedirectResponse("/login?reset=1", status_code=303)


@router.get("/login")
def user_login_page(request: Request, next: str = ""):
    if getattr(request.state, "user", None) is not None:
        return RedirectResponse("/", status_code=303)
    return templates.TemplateResponse(
        request=request,
        name="account/login.html",
        context={
            "app_name": settings.app_name,
            "next": safe_next(next),
        },
    )


@router.post("/login")
def user_login(
    request: Request,
    db: DbSession,
    email: str = Form(...),
    password: str = Form(...),
    next: str = Form(""),
    _csrf: None = Depends(verify_csrf),
):
    email = email.strip().lower()
    ip = _client_ip(request)
    if _login_is_blocked(db, ip):
        return templates.TemplateResponse(
            request=request,
            name="account/login.html",
            context={
                "app_name": settings.app_name,
                "error": "尝试次数过多，请 5 分钟后再试。",
                "email": email,
                "next": safe_next(next),
            },
            status_code=429,
            headers={"Retry-After": str(LOGIN_WINDOW_SECONDS)},
        )

    user = db.scalar(select(User).where(User.email == email))
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
            name="account/login.html",
            context={
                "app_name": settings.app_name,
                "error": "邮箱或密码错误",
                "email": email,
                "next": safe_next(next),
            },
            status_code=400,
        )

    if not user.is_active:
        return templates.TemplateResponse(
            request=request,
            name="account/login.html",
            context={
                "app_name": settings.app_name,
                "error": "账号已被禁用，请联系管理员。",
                "email": email,
                "next": safe_next(next),
            },
            status_code=403,
        )

    clear_bucket(db, _login_bucket(ip))
    request.session["user_id"] = user.id
    request.session["user_name"] = user.username
    request.session["user_version"] = user.session_version
    return RedirectResponse(safe_next(next), status_code=303)


@router.get("/login/code")
def user_login_code_page(request: Request, db: DbSession, next: str = ""):
    if getattr(request.state, "user", None) is not None:
        return RedirectResponse("/", status_code=303)

    pending = request.session.get(SESSION_LOGIN_CODE)
    if pending is not None:
        if load_pending_code(db, pending, PURPOSE_LOGIN_CODE) is None:
            request.session.pop(SESSION_LOGIN_CODE, None)
            pending = None

    return templates.TemplateResponse(
        request=request,
        name="account/login_code.html",
        context={
            "app_name": settings.app_name,
            "pending": pending,
            "next": pending["next"] if pending is not None else safe_next(next),
        },
    )


@router.post("/login/code/send")
def user_login_code_send(
    request: Request,
    db: DbSession,
    email: str = Form(...),
    next: str = Form(""),
    _csrf: None = Depends(verify_csrf),
):
    email = email.strip().lower()
    if EMAIL_RE.fullmatch(email) is None:
        return templates.TemplateResponse(
            request=request,
            name="account/login_code.html",
            context={
                "app_name": settings.app_name,
                "error": "邮箱格式不正确。",
                "email": email,
                "next": safe_next(next),
            },
            status_code=400,
        )

    ip = _client_ip(request)
    if is_rate_limited(
        db,
        f"login_code_probe:{ip}",
        LOGIN_CODE_WINDOW_SECONDS,
        LOGIN_CODE_PROBE_MAX,
    ):
        return templates.TemplateResponse(
            request=request,
            name="account/login_code.html",
            context={
                "app_name": settings.app_name,
                "error": "请求过于频繁，请稍后再试。",
                "email": email,
                "next": safe_next(next),
            },
            status_code=429,
            headers={"Retry-After": str(LOGIN_CODE_WINDOW_SECONDS)},
        )
    record_event(db, f"login_code_probe:{ip}")

    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        return templates.TemplateResponse(
            request=request,
            name="account/login_code.html",
            context={
                "app_name": settings.app_name,
                "error": "该邮箱尚未注册，请先注册。",
                "email": email,
                "next": safe_next(next),
            },
            status_code=400,
        )

    if not user.is_active:
        return templates.TemplateResponse(
            request=request,
            name="account/login_code.html",
            context={
                "app_name": settings.app_name,
                "error": "账号已被禁用，请联系管理员。",
                "email": email,
                "next": safe_next(next),
            },
            status_code=403,
        )

    if _login_code_is_blocked(db, ip):
        return templates.TemplateResponse(
            request=request,
            name="account/login_code.html",
            context={
                "app_name": settings.app_name,
                "error": "请求过于频繁，请稍后再试。",
                "email": email,
                "next": safe_next(next),
            },
            status_code=429,
        )

    if _email_code_is_blocked(
        db,
        PURPOSE_LOGIN_CODE,
        email,
        LOGIN_CODE_WINDOW_SECONDS,
        LOGIN_CODE_MAX,
    ):
        return templates.TemplateResponse(
            request=request,
            name="account/login_code.html",
            context={
                "app_name": settings.app_name,
                "error": "该邮箱请求验证码过于频繁，请稍后再试。",
                "email": email,
                "next": safe_next(next),
            },
            status_code=429,
            headers={"Retry-After": str(LOGIN_CODE_WINDOW_SECONDS)},
        )

    row = send_verification_code(db, email, PURPOSE_LOGIN_CODE)
    if row is None:
        request.session.pop(SESSION_LOGIN_CODE, None)
        return templates.TemplateResponse(
            request=request,
            name="account/login_code.html",
            context={
                "app_name": settings.app_name,
                "error": "验证码发送失败，请检查 SMTP 配置或稍后再试。",
                "email": email,
                "next": safe_next(next),
            },
            status_code=503,
        )

    request.session[SESSION_LOGIN_CODE] = {
        "code_id": row.id,
        "email": email,
        "next": safe_next(next),
    }
    _record_email_code(db, PURPOSE_LOGIN_CODE, email)
    _record_login_code(db, ip)
    return RedirectResponse("/login/code", status_code=303)


@router.post("/login/code/verify")
def user_login_code_verify(
    request: Request,
    db: DbSession,
    code: str = Form(...),
    _csrf: None = Depends(verify_csrf),
):
    pending = request.session.get(SESSION_LOGIN_CODE)
    if pending is None:
        return RedirectResponse("/login/code", status_code=303)

    row = load_pending_code(db, pending, PURPOSE_LOGIN_CODE)
    if row is None:
        request.session.pop(SESSION_LOGIN_CODE, None)
        return RedirectResponse("/login/code", status_code=303)

    if not code_matches(row, code):
        if record_failed_code_attempt(db, row):
            request.session.pop(SESSION_LOGIN_CODE, None)
            return RedirectResponse("/login/code", status_code=303)

        return templates.TemplateResponse(
            request=request,
            name="account/login_code.html",
            context={
                "app_name": settings.app_name,
                "error": "验证码错误，请重试。",
                "pending": pending,
                "next": pending["next"],
            },
            status_code=400,
        )

    user = db.scalar(select(User).where(User.email == pending["email"]))
    if user is None:
        db.delete(row)
        db.commit()
        request.session.pop(SESSION_LOGIN_CODE, None)
        return templates.TemplateResponse(
            request=request,
            name="account/login_code.html",
            context={
                "app_name": settings.app_name,
                "error": "账号不存在，请重新登录。",
                "next": "/",
            },
            status_code=400,
        )

    if not user.is_active:
        db.delete(row)
        db.commit()
        request.session.pop(SESSION_LOGIN_CODE, None)
        return templates.TemplateResponse(
            request=request,
            name="account/login_code.html",
            context={
                "app_name": settings.app_name,
                "error": "账号已被禁用，请联系管理员。",
                "next": "/",
            },
            status_code=403,
        )

    db.delete(row)
    db.commit()
    request.session.pop(SESSION_LOGIN_CODE, None)
    request.session["user_id"] = user.id
    request.session["user_name"] = user.username
    request.session["user_version"] = user.session_version
    return RedirectResponse(safe_next(pending["next"]), status_code=303)


@router.post("/logout")
def user_logout(request: Request, _csrf: None = Depends(verify_csrf)):
    request.session.pop("user_id", None)
    request.session.pop("user_name", None)
    request.session.pop("user_version", None)
    return RedirectResponse("/", status_code=303)


@router.get("/account/delete")
def user_delete_page(request: Request):
    user = getattr(request.state, "user", None)
    if user is None:
        return RedirectResponse("/login?next=/account/delete", status_code=303)
    return templates.TemplateResponse(
        request=request,
        name="account/delete.html",
        context={
            "app_name": settings.app_name,
            "user": user,
        },
    )


@router.post("/account/delete")
def user_delete_account(
    request: Request,
    db: DbSession,
    password: str = Form(...),
    _csrf: None = Depends(verify_csrf),
):
    user = getattr(request.state, "user", None)
    if user is None:
        return RedirectResponse("/login?next=/account/delete", status_code=303)

    valid = False
    try:
        valid = password_hash.verify(password, user.password_hash)
    except UnknownHashError:
        valid = False

    if not valid:
        return templates.TemplateResponse(
            request=request,
            name="account/delete.html",
            context={
                "app_name": settings.app_name,
                "user": user,
                "error": "密码不正确，账号未注销。",
            },
            status_code=400,
        )

    email = user.email.strip().lower() if user.email else None
    db.delete(user)
    if email:
        db.execute(delete(VerificationCode).where(VerificationCode.email == email))
        block = db.scalar(
            select(EmailRegistrationBlock).where(EmailRegistrationBlock.email == email)
        )
        blocked_until = now_naive() + timedelta(hours=EMAIL_BLOCK_HOURS)
        if block is None:
            db.add(
                EmailRegistrationBlock(
                    email=email,
                    blocked_until=blocked_until,
                )
            )
        else:
            block.blocked_until = blocked_until
    db.commit()

    request.session.pop("user_id", None)
    request.session.pop("user_name", None)
    request.session.pop("user_version", None)
    request.session.pop(SESSION_REGISTER, None)
    request.session.pop(SESSION_LOGIN_CODE, None)
    request.session.pop(SESSION_RESET, None)
    return RedirectResponse("/login?deleted=1", status_code=303)
