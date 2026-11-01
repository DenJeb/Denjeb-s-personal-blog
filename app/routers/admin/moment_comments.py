"""
========== 后台动态评论管理 ==========
"""

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import func, select

from app.auth import CurrentAdmin
from app.config import settings
from app.csrf import verify_csrf
from app.deps import DbSession
from app.models import Moment, MomentComment
from app.routers.admin.common import PAGE_SIZE, moment_page, page_slice
from app.templating import templates

router = APIRouter()


@router.get("/moment-comments")
def admin_moment_comments(
    request: Request,
    _admin: CurrentAdmin,
    db: DbSession,
    page: int = Query(1, ge=1),
):
    total = db.scalar(select(func.count()).select_from(MomentComment)) or 0
    page, total_pages = page_slice(page, total)
    comments = db.scalars(
        select(MomentComment)
        .order_by(MomentComment.created_at.desc(), MomentComment.id.desc())
        .offset((page - 1) * PAGE_SIZE)
        .limit(PAGE_SIZE)
    ).all()
    moment_ids = {comment.moment_id for comment in comments}
    moment_pages = {}
    if moment_ids:
        moments = db.scalars(select(Moment).where(Moment.id.in_(moment_ids))).all()
        moment_pages = {moment.id: moment_page(db, moment) for moment in moments}
    return templates.TemplateResponse(
        request=request,
        name="admin/moment_comments.html",
        context={
            "app_name": settings.app_name,
            "comments": comments,
            "moment_pages": moment_pages,
            "total": total,
            "page": page,
            "total_pages": total_pages,
            "has_prev": page > 1,
            "has_next": page < total_pages,
            "saved": request.query_params.get("saved") == "1",
            "deleted": request.query_params.get("deleted") == "1",
        },
    )


@router.post("/moment-comments/{comment_id}/approve")
def moment_comment_approve(
    comment_id: int,
    _admin: CurrentAdmin,
    db: DbSession,
    page: int = Form(1, ge=1),
    _csrf: None = Depends(verify_csrf),
):
    comment = db.get(MomentComment, comment_id)
    if comment is None:
        raise HTTPException(status_code=404, detail="动态评论不存在！")

    comment.is_approved = not comment.is_approved
    db.commit()
    suffix = f"&page={page}" if page > 1 else ""
    return RedirectResponse(f"/admin/moment-comments?saved=1{suffix}", status_code=303)


@router.get("/moment-comments/{comment_id}/delete")
def moment_comment_delete_confirm(
    request: Request,
    _admin: CurrentAdmin,
    comment_id: int,
    db: DbSession,
    page: int = Query(1, ge=1),
):
    comment = db.get(MomentComment, comment_id)
    if comment is None:
        raise HTTPException(status_code=404, detail="动态评论不存在！")

    page_suffix = f"?page={page}" if page > 1 else ""
    return templates.TemplateResponse(
        request=request,
        name="admin/delete_confirm.html",
        context={
            "app_name": settings.app_name,
            "item_title": f"{comment.author_name}：{comment.content[:40]}",
            "item_type": "动态评论",
            "delete_url": f"/admin/moment-comments/{comment.id}/delete{page_suffix}",
            "cancel_url": f"/admin/moment-comments{page_suffix}",
        },
    )


@router.post("/moment-comments/{comment_id}/delete")
def moment_comment_delete(
    comment_id: int,
    _admin: CurrentAdmin,
    db: DbSession,
    page: int = Query(1, ge=1),
    _csrf: None = Depends(verify_csrf),
):
    comment = db.get(MomentComment, comment_id)
    if comment is None:
        raise HTTPException(status_code=404, detail="动态评论不存在！")

    db.delete(comment)
    db.commit()
    suffix = f"&page={page}" if page > 1 else ""
    return RedirectResponse(
        f"/admin/moment-comments?deleted=1{suffix}", status_code=303
    )
