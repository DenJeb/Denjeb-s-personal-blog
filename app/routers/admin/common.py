"""
========== 后台公共辅助 ==========
"""

import re
from datetime import date
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.markdown import render_markdown
from app.models import BlogPost, Note

APP_DIR = Path(__file__).resolve().parent.parent.parent
UPLOAD_DIR = APP_DIR / "static" / "uploads"
MAX_IMAGE_SIZE = 5 * 1024 * 1024
TITLE_MAX_LENGTH = 200
SUMMARY_MAX_LENGTH = 500
PAGE_SIZE = 20


def page_slice(page: int, total: int) -> tuple[int, int]:
    total_pages = max((total + PAGE_SIZE - 1) // PAGE_SIZE, 1)
    page = min(max(page, 1), total_pages)
    return page, total_pages


_UPLOAD_URL_RE = re.compile(r"/static/uploads/[A-Za-z0-9._/-]+")


def parse_tags(raw: str) -> list[str]:
    tags = []
    for tag in raw.replace("，", ",").split(","):
        tag = tag.strip()
        if tag and tag not in tags:
            tags.append(tag)
    return tags


def detect_image_extension(data: bytes) -> str | None:
    if data.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if data.startswith((b"GIF87a", b"GIF89a")):
        return ".gif"
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return ".webp"
    return None


def save_uploaded_image(upload: UploadFile) -> str:
    data = upload.file.read(MAX_IMAGE_SIZE + 1)
    if not data:
        raise ValueError("图片文件为空。")
    if len(data) > MAX_IMAGE_SIZE:
        raise ValueError("图片不能超过 5 MB。")

    extension = detect_image_extension(data)
    if extension is None:
        raise ValueError("只支持 JPG、PNG、GIF、WebP 图片。")

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid4().hex}{extension}"
    (UPLOAD_DIR / filename).write_bytes(data)
    return f"/static/uploads/{filename}"


def append_uploaded_image(
    content: str, image: UploadFile | None, image_alt: str
) -> tuple[str, str | None]:
    if image is None or not image.filename:
        return content, None
    try:
        image_url = save_uploaded_image(image)
    except ValueError as exc:
        return content, str(exc)

    alt = image_alt.strip().replace("[", "").replace("]", "") or "图片"
    return content.rstrip() + f"\n\n![{alt}]({image_url})\n", None


def upload_urls_in_text(*texts: str | None) -> set[str]:
    urls = set()
    for text in texts:
        if text:
            urls.update(_UPLOAD_URL_RE.findall(text))
    return urls


def all_referenced_upload_urls(db: Session) -> set[str]:
    urls = set()
    for post in db.scalars(select(BlogPost)).all():
        urls.update(upload_urls_in_text(post.content, post.content_html))
    for note in db.scalars(select(Note)).all():
        urls.update(upload_urls_in_text(note.content, note.content_html))
    return urls


def all_upload_urls() -> set[str]:
    if not UPLOAD_DIR.is_dir():
        return set()
    return {
        f"/static/uploads/{path.relative_to(UPLOAD_DIR).as_posix()}"
        for path in UPLOAD_DIR.rglob("*")
        if path.is_file()
    }


def delete_orphan_uploads(db: Session) -> None:
    delete_unreferenced_uploads(db, all_upload_urls() - all_referenced_upload_urls(db))


def delete_unreferenced_uploads(db: Session, candidates: set[str]) -> None:
    if not candidates:
        return

    still_used = all_referenced_upload_urls(db)
    upload_root = UPLOAD_DIR.resolve()
    for url in candidates - still_used:
        relative = url.removeprefix("/static/uploads/")
        path = (UPLOAD_DIR / relative).resolve()
        if upload_root not in path.parents:
            continue
        if path.is_file():
            try:
                path.unlink()
            except OSError:
                pass


def post_form_values(post: BlogPost) -> dict:
    return {
        "title": post.title,
        "summary": post.summary,
        "content": post.content,
        "published_at": post.published_at.isoformat(),
        "tags": ", ".join(post.tags or []),
        "is_published": post.is_published,
    }


def note_form_values(note: Note) -> dict:
    return {
        "title": note.title,
        "summary": note.summary,
        "content": note.content,
        "published_at": note.published_at.isoformat(),
        "tags": ", ".join(note.tags or []),
        "category_id": note.category_id,
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
    post: BlogPost,
    title: str,
    summary: str,
    content: str,
    published_date: date,
    tags: str,
    is_published: bool,
) -> None:
    post.title = title.strip()
    post.summary = summary.strip()
    post.content = content.strip()
    post.content_html = render_markdown(post.content)
    post.published_at = published_date
    post.tags = parse_tags(tags)
    post.is_published = is_published


def fill_note(
    note: Note,
    title: str,
    summary: str,
    content: str,
    published_date: date,
    tags: str,
    category_id: int,
) -> None:
    note.title = title.strip()
    note.summary = summary.strip()
    note.content = content.strip()
    note.content_html = render_markdown(note.content)
    note.published_at = published_date
    note.tags = parse_tags(tags)
    note.category_id = category_id
