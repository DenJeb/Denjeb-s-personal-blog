"""
========== 图片上传服务 ==========
"""

import re
from io import BytesIO
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile
from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import BlogPost

APP_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = APP_DIR / "static" / "uploads"
MAX_IMAGE_SIZE = 5 * 1024 * 1024
MAX_IMAGE_DIMENSION = 2000
MAX_IMAGE_PIXELS = 40_000_000
WEBP_QUALITY = 82

_UPLOAD_URL_RE = re.compile(r"/static/uploads/[A-Za-z0-9._/-]+")


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


def process_image(data: bytes) -> tuple[bytes, str]:
    if not data:
        raise ValueError("图片文件为空。")
    if len(data) > MAX_IMAGE_SIZE:
        raise ValueError("图片不能超过 5 MB。")

    extension = detect_image_extension(data)
    if extension is None:
        raise ValueError("只支持 JPG、PNG、GIF、WebP 图片。")

    try:
        with Image.open(BytesIO(data)) as image:
            if image.width * image.height > MAX_IMAGE_PIXELS:
                raise ValueError("图片尺寸过大。")
            if extension in {".gif", ".webp"}:
                return data, extension

            processed = ImageOps.exif_transpose(image)
            processed.thumbnail((MAX_IMAGE_DIMENSION, MAX_IMAGE_DIMENSION))
            if processed.mode in {"RGBA", "LA", "P"}:
                processed = processed.convert("RGBA")
            else:
                processed = processed.convert("RGB")

            buffer = BytesIO()
            processed.save(buffer, format="WEBP", quality=WEBP_QUALITY, method=6)
            return buffer.getvalue(), ".webp"
    except ValueError:
        raise
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError) as exc:
        raise ValueError("图片无法解析，请换一张。") from exc


def save_image_bytes(data: bytes) -> str:
    processed, extension = process_image(data)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid4().hex}{extension}"
    (UPLOAD_DIR / filename).write_bytes(processed)
    return f"/static/uploads/{filename}"


def save_uploaded_image(upload: UploadFile) -> str:
    data = upload.file.read(MAX_IMAGE_SIZE + 1)
    return save_image_bytes(data)


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


def delete_upload_by_path(db: Session, path: str) -> str:
    """删除一个未被引用的上传文件，返回 deleted/in_use/missing/invalid/error。"""
    relative = Path(path)
    if relative.is_absolute() or ".." in relative.parts:
        return "invalid"

    target = (UPLOAD_DIR / relative).resolve()
    root = UPLOAD_DIR.resolve()
    if root not in target.parents or not target.is_file():
        return "missing"

    url = f"/static/uploads/{relative.as_posix()}"
    if url in all_referenced_upload_urls(db):
        return "in_use"

    try:
        target.unlink()
    except OSError:
        return "error"
    return "deleted"
