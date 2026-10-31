"""
========== 图片管理测试 ==========
"""

import base64
from datetime import date
from pathlib import Path
from uuid import uuid4

from sqlalchemy import delete

from app.db import SessionLocal
from app.models import BlogPost
from app.routers.admin.common import delete_orphan_uploads
from tests.utils import csrf_token

UPLOAD_DIR = Path("app/static/uploads")
PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Wl2nQAAAABJRU5ErkJggg=="
)


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
