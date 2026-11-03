"""
========== 图片管理测试 ==========
"""

from datetime import date
from io import BytesIO
from pathlib import Path
from uuid import uuid4

import pytest
from PIL import Image
from sqlalchemy import delete
from starlette.datastructures import UploadFile

from app.db import SessionLocal
from app.models import BlogPost
from app.services import uploads
from app.services.uploads import (
    MAX_IMAGE_DIMENSION,
    MAX_IMAGE_SIZE,
    delete_orphan_uploads,
    process_image,
    save_uploaded_image,
)
from tests.utils import csrf_token, image_bytes

UPLOAD_DIR = Path("app/static/uploads")
PNG = image_bytes()


def _image_bytes(
    size: tuple[int, int] = (10, 10),
    fmt: str = "PNG",
    color: tuple[int, int, int] = (255, 0, 0),
) -> bytes:
    return image_bytes(size=size, fmt=fmt, color=color)


def test_delete_unreferenced_upload(admin_client):
    name = f"__pytest_upload_{uuid4().hex}.png"
    path = UPLOAD_DIR / name
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    path.write_bytes(PNG)
    try:
        page = admin_client.get("/admin/uploads")
        assert name in page.text
        assert "未引用" in page.text

        token = csrf_token(page.text)
        response = admin_client.post(
            "/admin/uploads/delete",
            data={"csrf_token": token, "path": name},
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert not path.exists()
    finally:
        if path.exists():
            path.unlink()


def test_referenced_upload_is_protected(admin_client):
    name = f"__pytest_ref_{uuid4().hex}.png"
    path = UPLOAD_DIR / name
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    path.write_bytes(PNG)
    post = None
    try:
        with SessionLocal() as db:
            post = BlogPost(
                title=f"__pytest_upload_ref_{uuid4().hex}",
                summary="",
                content=f"![x](/static/uploads/{name})",
                content_html=f'<img src="/static/uploads/{name}">',
                published_at=date(2026, 10, 30),
                tags=[],
            )
            db.add(post)
            db.commit()

        page = admin_client.get("/admin/uploads")
        assert name in page.text
        assert "已引用" in page.text

        token = csrf_token(page.text)
        response = admin_client.post(
            "/admin/uploads/delete",
            data={"csrf_token": token, "path": name},
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert response.headers["location"].endswith("?in_use=1")
        assert path.exists()
    finally:
        with SessionLocal() as db:
            if post is not None:
                db.execute(delete(BlogPost).where(BlogPost.id == post.id))
                db.commit()
        if path.exists():
            path.unlink()


def test_upload_path_traversal_rejected(admin_client):
    name = f"__pytest_traversal_{uuid4().hex}.png"
    token = csrf_token(admin_client.get("/admin/uploads").text)
    response = admin_client.post(
        "/admin/uploads/delete",
        data={"csrf_token": token, "path": f"../{name}"},
        follow_redirects=False,
    )
    assert response.status_code == 400


def test_delete_orphan_uploads():
    name = f"__pytest_orphan_{uuid4().hex}.png"
    path = UPLOAD_DIR / name
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    path.write_bytes(PNG)
    try:
        with SessionLocal() as db:
            delete_orphan_uploads(db)
        assert not path.exists()
    finally:
        if path.exists():
            path.unlink()


def test_process_image_converts_png_to_webp():
    data, extension = process_image(_image_bytes(size=(10, 10)))
    assert extension == ".webp"
    assert data[:4] == b"RIFF" and data[8:12] == b"WEBP"


def test_process_image_resizes_large_image():
    data, _ = process_image(_image_bytes(size=(3000, 1000), fmt="JPEG"))
    with Image.open(BytesIO(data)) as image:
        assert max(image.size) == MAX_IMAGE_DIMENSION


def test_process_image_applies_exif_orientation():
    image = Image.new("RGB", (40, 20), (255, 0, 0))
    exif = image.getexif()
    exif[274] = 6
    buffer = BytesIO()
    image.save(buffer, format="JPEG", exif=exif)

    data, _ = process_image(buffer.getvalue())
    with Image.open(BytesIO(data)) as result:
        assert result.size == (20, 40)


def test_process_image_keeps_gif_bytes():
    data = _image_bytes(size=(10, 10), fmt="GIF")
    assert process_image(data) == (data, ".gif")


def test_process_image_rejects_corrupt_image():
    with pytest.raises(ValueError, match="无法解析"):
        process_image(b"\x89PNG\r\n\x1a\nnot really a png")


def test_process_image_rejects_decompression_bomb(monkeypatch):
    monkeypatch.setattr(uploads, "MAX_IMAGE_PIXELS", 10)
    with pytest.raises(ValueError, match="尺寸过大"):
        process_image(_image_bytes(size=(20, 20)))


def test_save_uploaded_image_rejects_large_file():
    upload = UploadFile(
        filename="big.png",
        file=BytesIO(b"x" * (MAX_IMAGE_SIZE + 1)),
    )
    with pytest.raises(ValueError, match="5 MB"):
        save_uploaded_image(upload)
