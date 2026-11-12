"""
========== 后台普通用户管理 ==========
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import func, select

from app.auth import CurrentAdmin
from app.config import settings
from app.csrf import verify_csrf
from app.deps import DbSession
from app.models import User
from app.routers.admin.common import PAGE_SIZE, page_slice
from app.services.accounts import delete_user, toggle_user
from app.templating import templates

router = APIRouter()


@router.get("/users")
def admin_users(
    request: Request,
    _admin: CurrentAdmin,
    db: DbSession,
    page: int = Query(1, ge=1),
):
    total = db.scalar(select(func.count()).select_from(User)) or 0
    page, total_pages = page_slice(page, total)
    users = db.scalars(
        select(User)
        .order_by(User.created_at.desc())
        .offset((page - 1) * PAGE_SIZE)
        .limit(PAGE_SIZE)
    ).all()
    return templates.TemplateResponse(
        request=request,
        name="admin/users.html",
        context={
            "app_name": settings.app_name,
            "users": users,
            "total": total,
            "page": page,
            "total_pages": total_pages,
            "has_prev": page > 1,
            "has_next": page < total_pages,
            "saved": request.query_params.get("saved") == "1",
            "deleted": request.query_params.get("deleted") == "1",
        },
    )


@router.post("/users/{user_id}/toggle")
def user_toggle(
    user_id: int,
    _admin: CurrentAdmin,
    db: DbSession,
    _csrf: None = Depends(verify_csrf),
):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="用户不存在！")

    toggle_user(db, user)
    return RedirectResponse("/admin/users?saved=1", status_code=303)


@router.get("/users/{user_id}/delete")
def user_delete_confirm(
    request: Request, _admin: CurrentAdmin, user_id: int, db: DbSession
):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="用户不存在！")

    return templates.TemplateResponse(
        request=request,
        name="admin/delete_confirm.html",
        context={
            "app_name": settings.app_name,
            "item_title": f"{user.email or ''} / {user.username}",
            "item_type": "用户",
            "delete_url": f"/admin/users/{user.id}/delete",
            "cancel_url": "/admin/users",
        },
    )


@router.post("/users/{user_id}/delete")
def user_delete(
    user_id: int,
    _admin: CurrentAdmin,
    db: DbSession,
    _csrf: None = Depends(verify_csrf),
):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="用户不存在！")

    delete_user(db, user)
    return RedirectResponse("/admin/users?deleted=1", status_code=303)
