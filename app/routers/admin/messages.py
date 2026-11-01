"""
========== 后台留言管理 ==========
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import func, select

from app.auth import CurrentAdmin
from app.config import settings
from app.csrf import verify_csrf
from app.deps import DbSession
from app.models import Message
from app.routers.admin.common import PAGE_SIZE, page_slice
from app.templating import templates

router = APIRouter()


@router.get("/messages")
def admin_messages(
    request: Request,
    _admin: CurrentAdmin,
    db: DbSession,
    page: int = Query(1, ge=1),
):
    total = db.scalar(select(func.count()).select_from(Message)) or 0
    page, total_pages = page_slice(page, total)
    messages = db.scalars(
        select(Message)
        .order_by(Message.created_at.desc(), Message.id.desc())
        .offset((page - 1) * PAGE_SIZE)
        .limit(PAGE_SIZE)
    ).all()
    return templates.TemplateResponse(
        request=request,
        name="admin/messages.html",
        context={
            "app_name": settings.app_name,
            "messages": messages,
            "total": total,
            "page": page,
            "total_pages": total_pages,
            "has_prev": page > 1,
            "has_next": page < total_pages,
            "deleted": request.query_params.get("deleted") == "1",
        },
    )


@router.get("/messages/{message_id}/delete")
def message_delete_confirm(
    request: Request,
    _admin: CurrentAdmin,
    message_id: int,
    db: DbSession,
    page: int = Query(1, ge=1),
):
    message = db.get(Message, message_id)
    if message is None:
        raise HTTPException(status_code=404, detail="留言不存在！")

    page_suffix = f"?page={page}" if page > 1 else ""
    return templates.TemplateResponse(
        request=request,
        name="admin/delete_confirm.html",
        context={
            "app_name": settings.app_name,
            "item_title": f"{message.author_name}：{message.content[:40]}",
            "item_type": "留言",
            "delete_url": f"/admin/messages/{message.id}/delete{page_suffix}",
            "cancel_url": f"/admin/messages{page_suffix}",
        },
    )


@router.post("/messages/{message_id}/delete")
def message_delete(
    message_id: int,
    _admin: CurrentAdmin,
    db: DbSession,
    page: int = Query(1, ge=1),
    _csrf: None = Depends(verify_csrf),
):
    message = db.get(Message, message_id)
    if message is None:
        raise HTTPException(status_code=404, detail="留言不存在！")

    db.delete(message)
    db.commit()
    suffix = f"&page={page}" if page > 1 else ""
    return RedirectResponse(f"/admin/messages?deleted=1{suffix}", status_code=303)
