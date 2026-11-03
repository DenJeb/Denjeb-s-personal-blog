"""
========== 后台评论管理 ==========
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.auth import CurrentAdmin
from app.config import settings
from app.csrf import verify_csrf
from app.deps import DbSession
from app.models import Comment
from app.routers.admin.common import PAGE_SIZE, page_slice
from app.templating import templates

router = APIRouter()


@router.get("/comments")
def admin_comments(
    request: Request,
    _admin: CurrentAdmin,
    db: DbSession,
    page: int = Query(1, ge=1),
):
    total = db.scalar(select(func.count()).select_from(Comment)) or 0
    page, total_pages = page_slice(page, total)
    comments = db.scalars(
        select(Comment)
        .options(selectinload(Comment.post))
        .order_by(Comment.created_at.desc())
        .offset((page - 1) * PAGE_SIZE)
        .limit(PAGE_SIZE)
    ).all()
    return templates.TemplateResponse(
        request=request,
        name="admin/comments.html",
        context={
            "app_name": settings.app_name,
            "comments": comments,
            "total": total,
            "page": page,
            "total_pages": total_pages,
            "has_prev": page > 1,
            "has_next": page < total_pages,
            "saved": request.query_params.get("saved") == "1",
            "deleted": request.query_params.get("deleted") == "1",
        },
    )


@router.post("/comments/{comment_id}/approve")
def comment_approve(
    request: Request,
    comment_id: int,
    _admin: CurrentAdmin,
    db: DbSession,
    _csrf: None = Depends(verify_csrf),
):
    comment = db.get(Comment, comment_id)
    if comment is None:
        raise HTTPException(status_code=404, detail="评论不存在！")

    comment.is_approved = not comment.is_approved
    db.commit()
    if request.headers.get("HX-Request") == "true":
        return templates.TemplateResponse(
            request=request,
            name="admin/_comment_row.html",
            context={"comment": comment},
        )
    return RedirectResponse("/admin/comments?saved=1", status_code=303)


@router.get("/comments/{comment_id}/delete")
def comment_delete_confirm(
    request: Request, _admin: CurrentAdmin, comment_id: int, db: DbSession
):
    comment = db.get(Comment, comment_id)
    if comment is None:
        raise HTTPException(status_code=404, detail="评论不存在！")

    return templates.TemplateResponse(
        request=request,
        name="admin/delete_confirm.html",
        context={
            "app_name": settings.app_name,
            "item_title": f"{comment.author_name}：{comment.content[:40]}",
            "item_type": "评论",
            "delete_url": f"/admin/comments/{comment.id}/delete",
            "cancel_url": "/admin/comments",
        },
    )


@router.post("/comments/{comment_id}/delete")
def comment_delete(
    comment_id: int,
    _admin: CurrentAdmin,
    db: DbSession,
    _csrf: None = Depends(verify_csrf),
):
    comment = db.get(Comment, comment_id)
    if comment is None:
        raise HTTPException(status_code=404, detail="评论不存在！")

    db.delete(comment)
    db.commit()
    return RedirectResponse("/admin/comments?deleted=1", status_code=303)
