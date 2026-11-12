"""
========== 后台评论审核 JSON API ==========
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select

from app.auth import CurrentAdminApi
from app.csrf import verify_csrf_header
from app.deps import DbSession
from app.models import Moment
from app.routers.api.admin_common import page_meta
from app.schemas.admin import (
    AdminCommentItem,
    AdminCommentList,
    AdminMomentCommentItem,
    AdminMomentCommentList,
    AdminToggleResponse,
)
from app.services.comments import (
    delete_comment,
    delete_moment_comment,
    paginate_admin_comments,
    paginate_admin_moment_comments,
    toggle_comment,
    toggle_moment_comment,
)
from app.services.content import moment_page

router = APIRouter(prefix="/admin")


@router.get("/comments", response_model=AdminCommentList)
def comments(
    _admin: CurrentAdminApi,
    db: DbSession,
    page: int = Query(1, ge=1),
):
    comments, total, page, total_pages = paginate_admin_comments(db, page)
    return AdminCommentList(
        items=[
            AdminCommentItem(
                id=comment.id,
                post_id=comment.post_id,
                post_title=comment.post.title,
                post_slug=comment.post.slug,
                author_name=comment.author_name,
                content=comment.content,
                created_at=comment.created_at,
                is_approved=comment.is_approved,
            )
            for comment in comments
        ],
        meta=page_meta(page, total, total_pages),
    )


@router.post(
    "/comments/{comment_id}/approve",
    response_model=AdminToggleResponse,
)
def approve_comment(
    comment_id: int,
    _admin: CurrentAdminApi,
    db: DbSession,
    _csrf: None = Depends(verify_csrf_header),
):
    comment = toggle_comment(db, comment_id)
    if comment is None:
        raise HTTPException(status_code=404, detail="评论不存在！")
    return AdminToggleResponse(is_approved=comment.is_approved)


@router.delete(
    "/comments/{comment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_comment(
    comment_id: int,
    _admin: CurrentAdminApi,
    db: DbSession,
    _csrf: None = Depends(verify_csrf_header),
):
    if not delete_comment(db, comment_id):
        raise HTTPException(status_code=404, detail="评论不存在！")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/moment-comments",
    response_model=AdminMomentCommentList,
)
def moment_comments(
    _admin: CurrentAdminApi,
    db: DbSession,
    page: int = Query(1, ge=1),
):
    comments, total, page, total_pages = paginate_admin_moment_comments(db, page)
    moment_ids = {comment.moment_id for comment in comments}
    moments = (
        {
            moment.id: moment
            for moment in db.scalars(
                select(Moment).where(Moment.id.in_(moment_ids))
            ).all()
        }
        if moment_ids
        else {}
    )
    pages = {
        moment_id: moment_page(db, moment) for moment_id, moment in moments.items()
    }

    return AdminMomentCommentList(
        items=[
            AdminMomentCommentItem(
                id=comment.id,
                moment_id=comment.moment_id,
                moment_page=pages.get(comment.moment_id, 1),
                author_name=comment.author_name,
                content=comment.content,
                created_at=comment.created_at,
                is_approved=comment.is_approved,
            )
            for comment in comments
        ],
        meta=page_meta(page, total, total_pages),
    )


@router.post(
    "/moment-comments/{comment_id}/approve",
    response_model=AdminToggleResponse,
)
def approve_moment_comment(
    comment_id: int,
    _admin: CurrentAdminApi,
    db: DbSession,
    _csrf: None = Depends(verify_csrf_header),
):
    comment = toggle_moment_comment(db, comment_id)
    if comment is None:
        raise HTTPException(status_code=404, detail="动态评论不存在！")
    return AdminToggleResponse(is_approved=comment.is_approved)


@router.delete(
    "/moment-comments/{comment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_moment_comment(
    comment_id: int,
    _admin: CurrentAdminApi,
    db: DbSession,
    _csrf: None = Depends(verify_csrf_header),
):
    if not delete_moment_comment(db, comment_id):
        raise HTTPException(status_code=404, detail="动态评论不存在！")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
