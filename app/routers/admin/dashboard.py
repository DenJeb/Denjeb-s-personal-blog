"""
========== 后台首页 ==========
"""

from fastapi import APIRouter, Request
from sqlalchemy import func, select

from app.auth import CurrentAdmin
from app.config import settings
from app.deps import DbSession
from app.models import BlogPost, Comment, Message, Moment, MomentComment, User
from app.templating import templates

router = APIRouter()


@router.get("/")
def dashboard(request: Request, admin: CurrentAdmin, db: DbSession):
    post_count = db.scalar(select(func.count()).select_from(BlogPost)) or 0
    moment_count = db.scalar(select(func.count()).select_from(Moment)) or 0
    message_count = db.scalar(select(func.count()).select_from(Message)) or 0
    comment_count = db.scalar(select(func.count()).select_from(Comment)) or 0
    moment_comment_count = (
        db.scalar(select(func.count()).select_from(MomentComment)) or 0
    )
    user_count = db.scalar(select(func.count()).select_from(User)) or 0
    pending_count = (
        db.scalar(
            select(func.count())
            .select_from(Comment)
            .where(Comment.is_approved.is_(False))
        )
        or 0
    )
    moment_pending_count = (
        db.scalar(
            select(func.count())
            .select_from(MomentComment)
            .where(MomentComment.is_approved.is_(False))
        )
        or 0
    )
    return templates.TemplateResponse(
        request=request,
        name="admin/dashboard.html",
        context={
            "app_name": settings.app_name,
            "admin": admin,
            "post_count": post_count,
            "moment_count": moment_count,
            "message_count": message_count,
            "comment_count": comment_count,
            "moment_comment_count": moment_comment_count,
            "user_count": user_count,
            "pending_count": pending_count,
            "moment_pending_count": moment_pending_count,
        },
    )
