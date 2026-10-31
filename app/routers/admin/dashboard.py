"""
========== 后台首页 ==========
"""

from fastapi import APIRouter, Request
from sqlalchemy import func, select

from app.auth import CurrentAdmin
from app.config import settings
from app.deps import DbSession
from app.models import BlogPost, Comment, Note, User
from app.templating import templates

router = APIRouter()


@router.get("/")
def dashboard(request: Request, admin: CurrentAdmin, db: DbSession):
    post_count = db.scalar(select(func.count()).select_from(BlogPost)) or 0
    note_count = db.scalar(select(func.count()).select_from(Note)) or 0
    comment_count = db.scalar(select(func.count()).select_from(Comment)) or 0
    user_count = db.scalar(select(func.count()).select_from(User)) or 0
    pending_count = (
        db.scalar(
            select(func.count())
            .select_from(Comment)
            .where(Comment.is_approved.is_(False))
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
            "note_count": note_count,
            "comment_count": comment_count,
            "user_count": user_count,
            "pending_count": pending_count,
        },
    )
