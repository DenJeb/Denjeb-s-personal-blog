"""
========== 后台公共辅助 ==========
"""

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.constants import MOMENTS_PER_PAGE
from app.markdown import render_markdown_with_toc
from app.models import BlogPost, Moment
from app.services.content import unique_post_slug

TITLE_MAX_LENGTH = 200
SUMMARY_MAX_LENGTH = 500
PAGE_SIZE = 20


def page_slice(page: int, total: int) -> tuple[int, int]:
    total_pages = max((total + PAGE_SIZE - 1) // PAGE_SIZE, 1)
    page = min(max(page, 1), total_pages)
    return page, total_pages


def moment_page(db: Session, moment: Moment) -> int:
    """动态在公开时间线里的页码。"""
    ranked = select(
        Moment.id.label("id"),
        func.row_number()
        .over(order_by=(Moment.created_at.desc(), Moment.id.desc()))
        .label("rn"),
    ).subquery()
    position = db.scalar(select(ranked.c.rn).where(ranked.c.id == moment.id))
    if position is None:
        return 1
    return (position - 1) // MOMENTS_PER_PAGE + 1


def parse_tags(raw: str) -> list[str]:
    tags = []
    for tag in raw.replace("，", ",").split(","):
        tag = tag.strip()
        if tag and tag not in tags:
            tags.append(tag)
    return tags


def post_form_values(post: BlogPost) -> dict:
    return {
        "title": post.title,
        "slug": post.slug or "",
        "summary": post.summary,
        "content": post.content,
        "published_at": post.published_at.isoformat(),
        "tags": ", ".join(post.tags or []),
        "is_published": post.is_published,
    }


def validate_content_fields(
    title: str, summary: str, content: str, published_at: str
) -> tuple[str | None, date | None]:
    error = None
    published_date = None
    try:
        published_date = date.fromisoformat(published_at)
    except ValueError:
        error = "发布日期格式不正确，应为 YYYY-MM-DD。"

    if len(title.strip()) > TITLE_MAX_LENGTH:
        error = f"标题不能超过 {TITLE_MAX_LENGTH} 个字符。"
    elif not title.strip():
        error = "标题不能为空。"
    elif len(summary) > SUMMARY_MAX_LENGTH:
        error = f"摘要不能超过 {SUMMARY_MAX_LENGTH} 个字符。"
    elif not content.strip():
        error = "正文不能为空。"

    return error, published_date


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
    post.title = title.strip()
    post.slug = unique_post_slug(
        db,
        post.title,
        post_id=post.id,
        requested=slug or post.slug or "",
    )
    post.summary = summary.strip()
    post.content = content.strip()
    post.content_html, _ = render_markdown_with_toc(post.content)
    post.published_at = published_date
    post.tags = parse_tags(tags)
    post.is_published = is_published
