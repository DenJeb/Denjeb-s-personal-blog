"""
========== 后台 JSON API（Phase 3a：仪表盘与文章读取） ==========
"""

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select

from app.auth import CurrentAdminApi
from app.deps import DbSession
from app.models import BlogPost, Comment, Message, Moment, MomentComment, User
from app.routers.admin.common import PAGE_SIZE, page_slice
from app.schemas.admin import (
    AdminDashboard,
    AdminMe,
    AdminPostDetail,
    AdminPostList,
    AdminPostSummary,
)
from app.schemas.public import PageMeta
from app.services.content import reading_minutes

router = APIRouter()


def _summary(post: BlogPost) -> AdminPostSummary:
    return AdminPostSummary(
        id=post.id,
        title=post.title,
        slug=post.slug,
        summary=post.summary,
        published_at=post.published_at,
        is_published=post.is_published,
        tags=list(post.tags or []),
        reading_minutes=reading_minutes(post.content),
    )


def _meta(page: int, per_page: int, total: int, total_pages: int) -> PageMeta:
    return PageMeta(
        page=page,
        per_page=per_page,
        total=total,
        total_pages=total_pages,
        has_prev=page > 1,
        has_next=page < total_pages,
    )


@router.get("/admin/me", response_model=AdminMe, name="admin_api_me")
def admin_me(admin: CurrentAdminApi):
    return AdminMe(username=admin.username, email=admin.email)


@router.get(
    "/admin/dashboard", response_model=AdminDashboard, name="admin_api_dashboard"
)
def dashboard(_admin: CurrentAdminApi, db: DbSession):
    return AdminDashboard(
        post_count=db.scalar(select(func.count()).select_from(BlogPost)) or 0,
        moment_count=db.scalar(select(func.count()).select_from(Moment)) or 0,
        message_count=db.scalar(select(func.count()).select_from(Message)) or 0,
        comment_count=db.scalar(select(func.count()).select_from(Comment)) or 0,
        moment_comment_count=(
            db.scalar(select(func.count()).select_from(MomentComment)) or 0
        ),
        user_count=db.scalar(select(func.count()).select_from(User)) or 0,
        pending_count=(
            db.scalar(
                select(func.count())
                .select_from(Comment)
                .where(Comment.is_approved.is_(False))
            )
            or 0
        ),
        moment_pending_count=(
            db.scalar(
                select(func.count())
                .select_from(MomentComment)
                .where(MomentComment.is_approved.is_(False))
            )
            or 0
        ),
    )


@router.get("/admin/posts", response_model=AdminPostList, name="admin_api_posts")
def posts(
    _admin: CurrentAdminApi,
    db: DbSession,
    page: int = Query(1, ge=1),
):
    total = db.scalar(select(func.count()).select_from(BlogPost)) or 0
    page, total_pages = page_slice(page, total)
    items = db.scalars(
        select(BlogPost)
        .order_by(BlogPost.published_at.desc(), BlogPost.id.desc())
        .offset((page - 1) * PAGE_SIZE)
        .limit(PAGE_SIZE)
    ).all()

    return AdminPostList(
        items=[_summary(post) for post in items],
        meta=_meta(page, PAGE_SIZE, total, total_pages),
    )


@router.get(
    "/admin/posts/{post_id}",
    response_model=AdminPostDetail,
    name="admin_api_post_detail",
)
def post_detail(
    post_id: int,
    _admin: CurrentAdminApi,
    db: DbSession,
):
    post = db.get(BlogPost, post_id)
    if post is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文章不存在！",
        )

    return AdminPostDetail(
        **_summary(post).model_dump(),
        content=post.content,
        content_html=post.content_html,
    )
