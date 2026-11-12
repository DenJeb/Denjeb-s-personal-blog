"""
========== 后台 JSON API 公共辅助 ==========
"""

from app.models import BlogPost
from app.schemas.admin import AdminPostSummary
from app.schemas.public import PageMeta
from app.services.content import reading_minutes
from app.services.pagination import ADMIN_PAGE_SIZE
from app.time_utils import site_today


def post_summary(post: BlogPost) -> AdminPostSummary:
    return AdminPostSummary(
        id=post.id,
        title=post.title,
        slug=post.slug,
        summary=post.summary,
        published_at=post.published_at,
        is_published=post.is_published,
        is_public=post.is_published and post.published_at <= site_today(),
        tags=list(post.tags or []),
        reading_minutes=reading_minutes(post.content),
    )


def page_meta(page: int, total: int, total_pages: int) -> PageMeta:
    return PageMeta(
        page=page,
        per_page=ADMIN_PAGE_SIZE,
        total=total,
        total_pages=total_pages,
        has_prev=page > 1,
        has_next=page < total_pages,
    )
