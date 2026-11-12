"""
========== 后台 JSON API（Phase 3a：仪表盘与文章读取） ==========
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select

from app.auth import CurrentAdminApi
from app.csrf import verify_csrf_header
from app.deps import DbSession
from app.models import BlogPost, Comment, Message, Moment, MomentComment, User
from app.routers.admin.common import PAGE_SIZE, page_slice
from app.routers.api import admin_content, admin_moderation, admin_settings
from app.routers.api.admin_common import page_meta, post_summary
from app.schemas.admin import (
    AdminDashboard,
    AdminMe,
    AdminPostDetail,
    AdminPostList,
)
from app.schemas.auth import LogoutResponse

router = APIRouter()
router.include_router(admin_moderation.router)
router.include_router(admin_content.router)
router.include_router(admin_settings.router)


@router.post("/admin/logout", response_model=LogoutResponse, name="admin_api_logout")
def admin_logout(
    request: Request,
    _csrf: None = Depends(verify_csrf_header),
):
    for key in (
        "admin_user_id",
        "admin_version",
        "pending_admin_id",
        "pending_admin_version",
        "pending_admin_at",
        "pending_admin_login_code",
        "pending_totp_secret",
    ):
        request.session.pop(key, None)
    return LogoutResponse(ok=True)


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
        items=[post_summary(post) for post in items],
        meta=page_meta(page, total, total_pages),
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
        **post_summary(post).model_dump(),
        content=post.content,
        content_html=post.content_html,
    )
