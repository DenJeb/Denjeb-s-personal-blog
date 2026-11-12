"""
========== 后台文章写入服务 ==========

Jinja2 后台与 JSON API 共用同一套字段校验、slug 生成、Markdown 渲染和
上传图片清理逻辑。
"""

from datetime import date

from sqlalchemy.orm import Session

from app.markdown import render_markdown, render_markdown_with_toc
from app.models import BlogPost
from app.services.content import unique_post_slug
from app.services.uploads import delete_unreferenced_uploads, upload_urls_in_text

TITLE_MAX_LENGTH = 200
SUMMARY_MAX_LENGTH = 500


def parse_tags(raw: str | list[str]) -> list[str]:
    parts = [raw] if isinstance(raw, str) else raw

    tags: list[str] = []
    for item in parts:
        for tag in str(item).replace("，", ",").split(","):
            tag = tag.strip()
            if tag and tag not in tags:
                tags.append(tag)
    return tags


def validate_post_fields(
    title: str,
    summary: str,
    content: str,
    published_at: str | date,
) -> tuple[str | None, date | None]:
    error = None
    published_date = None

    if isinstance(published_at, date):
        published_date = published_at
    else:
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


def apply_post_fields(
    db: Session,
    post: BlogPost,
    *,
    title: str,
    summary: str,
    content: str,
    published_at: date,
    tags: list[str],
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
    post.published_at = published_at
    post.tags = list(tags)
    post.is_published = is_published


def create_post(
    db: Session,
    *,
    title: str,
    summary: str,
    content: str,
    published_at: date,
    tags: list[str],
    is_published: bool,
    slug: str = "",
) -> BlogPost:
    post = BlogPost()
    apply_post_fields(
        db,
        post,
        title=title,
        summary=summary,
        content=content,
        published_at=published_at,
        tags=tags,
        is_published=is_published,
        slug=slug,
    )
    db.add(post)
    db.commit()
    db.refresh(post)
    return post


def update_post(
    db: Session,
    post: BlogPost,
    *,
    title: str,
    summary: str,
    content: str,
    published_at: date,
    tags: list[str],
    is_published: bool,
    slug: str = "",
) -> BlogPost:
    old_urls = upload_urls_in_text(post.content, post.content_html)
    apply_post_fields(
        db,
        post,
        title=title,
        summary=summary,
        content=content,
        published_at=published_at,
        tags=tags,
        is_published=is_published,
        slug=slug,
    )
    db.commit()
    db.refresh(post)
    delete_unreferenced_uploads(db, old_urls)
    return post


def delete_post(db: Session, post: BlogPost) -> None:
    candidates = upload_urls_in_text(post.content, post.content_html)
    db.delete(post)
    db.commit()
    delete_unreferenced_uploads(db, candidates)


def preview_html(content: str) -> str:
    return render_markdown(content)
