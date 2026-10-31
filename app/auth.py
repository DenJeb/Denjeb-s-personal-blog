"""
========== 后台认证依赖 ==========
"""

from typing import Annotated

from fastapi import Depends, HTTPException, Request, status

from app.config import settings
from app.deps import DbSession
from app.models import AdminUser


def require_admin(request: Request, db: DbSession) -> AdminUser:
    user_id = request.session.get("admin_user_id")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            headers={"Location": "/admin/login"},
        )

    user = db.get(AdminUser, user_id)
    if (
        user is None
        or (user.email or "").lower() != settings.admin_email_normalized
        or request.session.get("admin_version") != user.session_version
    ):
        request.session.pop("admin_user_id", None)
        request.session.pop("admin_version", None)
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            headers={"Location": "/admin/login"},
        )
    return user


CurrentAdmin = Annotated[AdminUser, Depends(require_admin)]
