"""
========== 后台用户与安全设置 JSON API ==========
"""

import pyotp
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy import func, select

from app.auth import CurrentAdminApi
from app.config import settings
from app.csrf import verify_csrf_header
from app.deps import DbSession
from app.models import User
from app.routers.api.admin_common import page_meta
from app.schemas.admin import (
    AdminOkResponse,
    AdminSecurity,
    AdminToggleResponse,
    AdminTotpDisableRequest,
    AdminTotpEnableRequest,
    AdminUserItem,
    AdminUserList,
)
from app.services.accounts import delete_user, toggle_user
from app.services.pagination import ADMIN_PAGE_SIZE, page_slice
from app.services.security import (
    disable_totp,
    enable_totp,
    provisioning_uri,
    verify_totp,
)

router = APIRouter(prefix="/admin")
PENDING_TOTP_SECRET = "pending_totp_secret"


def _security_state(request: Request, admin) -> AdminSecurity:
    if admin.totp_secret:
        return AdminSecurity(totp_enabled=True)

    secret = request.session.get(PENDING_TOTP_SECRET)
    if secret is None:
        return AdminSecurity(totp_enabled=False)

    return AdminSecurity(
        totp_enabled=False,
        setup_secret=secret,
        setup_uri=provisioning_uri(
            secret,
            admin.email or admin.username,
            settings.app_name,
        ),
    )


@router.get("/users", response_model=AdminUserList)
def list_users(
    _admin: CurrentAdminApi,
    db: DbSession,
    page: int = Query(1, ge=1),
):
    total = db.scalar(select(func.count()).select_from(User)) or 0
    page, total_pages = page_slice(page, total)
    users = db.scalars(
        select(User)
        .order_by(User.created_at.desc(), User.id.desc())
        .offset((page - 1) * ADMIN_PAGE_SIZE)
        .limit(ADMIN_PAGE_SIZE)
    ).all()

    return AdminUserList(
        items=[
            AdminUserItem(
                id=user.id,
                email=user.email,
                username=user.username,
                is_active=user.is_active,
                created_at=user.created_at,
            )
            for user in users
        ],
        meta=page_meta(page, total, total_pages),
    )


@router.post("/users/{user_id}/toggle", response_model=AdminToggleResponse)
def toggle_user_endpoint(
    user_id: int,
    _admin: CurrentAdminApi,
    db: DbSession,
    _csrf: None = Depends(verify_csrf_header),
):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="用户不存在！")

    toggle_user(db, user)
    return AdminToggleResponse(is_active=user.is_active)


@router.delete(
    "/users/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_user_endpoint(
    user_id: int,
    _admin: CurrentAdminApi,
    db: DbSession,
    _csrf: None = Depends(verify_csrf_header),
):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="用户不存在！")

    delete_user(db, user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/security", response_model=AdminSecurity)
def security_state(
    _admin: CurrentAdminApi,
    request: Request,
):
    return _security_state(request, _admin)


@router.post("/security/totp/start", response_model=AdminSecurity)
def totp_start(
    _admin: CurrentAdminApi,
    request: Request,
    _csrf: None = Depends(verify_csrf_header),
):
    if _admin.totp_secret is None:
        request.session[PENDING_TOTP_SECRET] = pyotp.random_base32()
    return _security_state(request, _admin)


@router.post("/security/totp/enable", response_model=AdminOkResponse)
def totp_enable(
    payload: AdminTotpEnableRequest,
    _admin: CurrentAdminApi,
    request: Request,
    db: DbSession,
    _csrf: None = Depends(verify_csrf_header),
):
    if _admin.totp_secret is not None:
        raise HTTPException(status_code=400, detail="两步验证已经启用。")

    secret = request.session.get(PENDING_TOTP_SECRET)
    if secret is None:
        raise HTTPException(status_code=400, detail="请先开始设置两步验证。")

    if not verify_totp(secret, payload.code):
        raise HTTPException(status_code=400, detail="验证码不正确，请重试。")

    enable_totp(db, _admin, secret)
    request.session.pop(PENDING_TOTP_SECRET, None)
    return AdminOkResponse(message="两步验证已启用。")


@router.post("/security/totp/disable", response_model=AdminOkResponse)
def totp_disable(
    payload: AdminTotpDisableRequest,
    _admin: CurrentAdminApi,
    request: Request,
    db: DbSession,
    _csrf: None = Depends(verify_csrf_header),
):
    if _admin.totp_secret is None:
        raise HTTPException(status_code=400, detail="两步验证未启用。")

    if not disable_totp(db, _admin, payload.password, payload.code):
        raise HTTPException(status_code=400, detail="密码或验证码不正确。")

    request.session["admin_version"] = _admin.session_version
    return AdminOkResponse(message="两步验证已关闭。")
