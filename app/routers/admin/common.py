"""
========== 后台公共辅助（兼容层） ==========

具体实现已经迁到 app.services，这里保留旧路由使用的名称。
"""

from datetime import date

from sqlalchemy.orm import Session

from app.models import BlogPost
from app.services.content import moment_page
from app.services.pagination import ADMIN_PAGE_SIZE as PAGE_SIZE
from app.services.pagination import page_slice
from app.services.posts import (
    SUMMARY_MAX_LENGTH,
    TITLE_MAX_LENGTH,
    apply_post_fields,
    parse_tags,
    post_form_values,
    validate_post_fields,
)

__all__ = [
    "PAGE_SIZE",
    "SUMMARY_MAX_LENGTH",
    "TITLE_MAX_LENGTH",
    "fill_post",
    "moment_page",
    "page_slice",
    "parse_tags",
    "post_form_values",
    "validate_content_fields",
]


def validate_content_fields(
    title: str, summary: str, content: str, published_at: str
) -> tuple[str | None, date | None]:
    return validate_post_fields(title, summary, content, published_at)


def fill_post(
    db: Session,
    post: BlogPost,
    title: str,
    summary: str,
    content: str,
    published_date: date,
    tags: str,
    is_published: bool,
    slug: str = "",
) -> None:
    apply_post_fields(
        db,
        post,
        title=title,
        summary=summary,
        content=content,
        published_at=published_date,
        tags=parse_tags(tags),
        is_published=is_published,
        slug=slug,
    )
