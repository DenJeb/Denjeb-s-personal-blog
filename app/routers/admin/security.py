"""
========== 后台安全设置：两步验证 ==========
"""

import pyotp
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from pwdlib import PasswordHash
from pwdlib.exceptions import UnknownHashError

from app.auth import CurrentAdmin
from app.config import settings
from app.csrf import verify_csrf
from app.deps import DbSession
from app.templating import templates

router = APIRouter()
password_hash = PasswordHash.recommended()

PENDING_TOTP_SECRET = "pending_totp_secret"


def _security_context(request: Request, admin, error: str | None = None) -> dict:
    setup_secret = request.session.get(PENDING_TOTP_SECRET)
    setup_uri = None
    if setup_secret:
        setup_uri = pyotp.TOTP(setup_secret).provisioning_uri(
            name=admin.email or admin.username,
            issuer_name=settings.app_name,
        )
    return {
        "app_name": settings.app_name,
        "admin": admin,
        "totp_enabled": bool(admin.totp_secret),
        "setup_secret": setup_secret,
        "setup_uri": setup_uri,
        "saved": request.query_params.get("saved") == "1",
        "error": error,
    }


@router.get("/security")
def security_page(request: Request, admin: CurrentAdmin):
    return templates.TemplateResponse(
        request=request,
        name="admin/security.html",
        context=_security_context(request, admin),
    )


@router.post("/security/totp/start")
def totp_start(
    request: Request,
    admin: CurrentAdmin,
    _csrf: None = Depends(verify_csrf),
):
    if admin.totp_secret:
        return RedirectResponse("/admin/security", status_code=303)

    request.session[PENDING_TOTP_SECRET] = pyotp.random_base32()
    return RedirectResponse("/admin/security?setup=1", status_code=303)


@router.post("/security/totp/enable")
def totp_enable(
    request: Request,
    admin: CurrentAdmin,
    db: DbSession,
    code: str = Form(...),
    _csrf: None = Depends(verify_csrf),
):
    if admin.totp_secret:
        return RedirectResponse("/admin/security", status_code=303)

    secret = request.session.get(PENDING_TOTP_SECRET)
    if not secret:
        return RedirectResponse("/admin/security", status_code=303)

    if not pyotp.TOTP(secret).verify(code.strip(), valid_window=1):
        return templates.TemplateResponse(
            request=request,
            name="admin/security.html",
            context=_security_context(request, admin, "验证码不正确，请重试。"),
            status_code=400,
        )

    admin.totp_secret = secret
    db.commit()
    request.session.pop(PENDING_TOTP_SECRET, None)
    return RedirectResponse("/admin/security?saved=1", status_code=303)


@router.post("/security/totp/disable")
def totp_disable(
    request: Request,
    admin: CurrentAdmin,
    db: DbSession,
    password: str = Form(...),
    code: str = Form(...),
    _csrf: None = Depends(verify_csrf),
):
    if not admin.totp_secret:
        return RedirectResponse("/admin/security", status_code=303)

    try:
        valid_password = password_hash.verify(password, admin.password_hash)
    except UnknownHashError:
        valid_password = False

    if not valid_password or not pyotp.TOTP(admin.totp_secret).verify(
        code.strip(), valid_window=1
    ):
        return templates.TemplateResponse(
            request=request,
            name="admin/security.html",
            context=_security_context(request, admin, "密码或验证码不正确。"),
            status_code=400,
        )

    admin.totp_secret = None
    admin.session_version += 1
    db.commit()
    request.session["admin_version"] = admin.session_version
    return RedirectResponse("/admin/security?saved=1", status_code=303)
