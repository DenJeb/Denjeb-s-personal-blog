"""
========== 后台认证依赖 ==========
"""

from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.config import settings
from app.deps import DbSession
from app.models import AdminUser, User


def current_admin(request: Request, db: Session) -> AdminUser | None:
    admin_id = request.session.get("admin_user_id")
    if admin_id is None:
        return None

    admin = db.get(AdminUser, admin_id)
    if (
        admin is None
        or (admin.email or "").lower() != settings.admin_email_normalized
        or request.session.get("admin_version") != admin.session_version
    ):
        request.session.pop("admin_user_id", None)
        request.session.pop("admin_version", None)
        return None
    return admin


def current_commenter(
    request: Request, db: Session
) -> tuple[str | None, str | None, int | None]:
    user: User | None = getattr(request.state, "user", None)
    if user is not None and user.is_active:
        return user.username, f"user:{user.id}", user.id

    admin = current_admin(request, db)
    if admin is not None:
        return admin.username, f"admin:{admin.id}", None
    return None, None, None


def require_admin(request: Request, db: DbSession) -> AdminUser:
    admin = current_admin(request, db)
    if admin is None:
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            headers={"Location": "/admin/login"},
        )
    return admin


CurrentAdmin = Annotated[AdminUser, Depends(require_admin)]


def require_admin_api(request: Request, db: DbSession) -> AdminUser:
    admin = current_admin(request, db)
    if admin is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="请先登录后台",
        )
    return admin


CurrentAdminApi = Annotated[AdminUser, Depends(require_admin_api)]
