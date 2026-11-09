"""
========== 后台功能测试 ==========
"""

import re
from pathlib import Path

from sqlalchemy import delete, select

from app.db import SessionLocal
from app.models import BlogPost
from tests.utils import csrf_token, image_bytes

POST_TITLE = "__pytest_post__"
PNG = image_bytes()
UPLOAD_DIR = Path("app/static/uploads")


def _cleanup_content() -> None:
    with SessionLocal() as db:
        db.execute(delete(BlogPost).where(BlogPost.title.like(POST_TITLE + "%")))
        db.commit()


def test_post_form_includes_editor(admin_client):
    response = admin_client.get("/admin/posts/new")
    assert response.status_code == 200
    assert "/static/js/editor.js" in response.text
    assert "/static/css/editor.css" in response.text
    assert "data-markdown-editor" in response.text
    assert 'name="content"' in response.text


def test_admin_pages(admin_client):
    for path in (
        "/admin/",
        "/admin/posts",
        "/admin/comments",
        "/admin/moments",
        "/admin/moment-comments",
        "/admin/messages",
        "/admin/uploads",
        "/admin/users",
        "/admin/security",
        "/admin/posts/1/edit",
    ):
        assert admin_client.get(path).status_code == 200, path


def test_login_page_minimal_layout(client):
    response = client.get("/admin/login")
    assert response.status_code == 200
    assert "后台登录" in response.text
    assert "归档" not in response.text
    assert 'id="theme-toggle"' in response.text
    # The form must target the Jinja login route, not /api/v1/auth/login.
    assert re.search(r'action="[^"]*/admin/login"', response.text)


def test_admin_shell_logout_targets_admin_route(admin_client):
    response = admin_client.get("/admin/")
    assert response.status_code == 200
    assert re.search(r'href="[^"]*/admin/"', response.text)
    assert re.search(r'action="[^"]*/admin/logout"', response.text)


def test_login_requires_csrf(client):
    page = client.get("/admin/login")
    assert page.status_code == 200
    csrf_token(page.text)

    missing = client.post(
        "/admin/login",
        data={"username": "x", "password": "y"},
        follow_redirects=False,
    )
    assert missing.status_code == 422

    wrong = client.post(
        "/admin/login",
        data={"username": "x", "password": "y", "csrf_token": "wrong"},
        follow_redirects=False,
    )
    assert wrong.status_code == 400


def test_post_crud_and_image_cleanup(admin_client):
    _cleanup_content()
    created_path = None
    try:
        token = csrf_token(admin_client.get("/admin/posts/new").text)
        response = admin_client.post(
            "/admin/posts/new",
            data={
                "csrf_token": token,
                "title": POST_TITLE,
                "summary": "pytest",
                "content": "## pytest",
                "published_at": "2026-10-30",
                "tags": "pytest",
                "image_alt": "测试图片",
            },
            files={"image": ("test.png", PNG, "image/png")},
            follow_redirects=False,
        )
        assert response.status_code == 303

        with SessionLocal() as db:
            post = db.scalar(select(BlogPost).where(BlogPost.title == POST_TITLE))
            assert post is not None
            post_id = post.id
            urls = re.findall(
                r"/static/uploads/[0-9a-f]+\.(?:jpg|png|gif|webp)",
                post.content,
            )
            assert len(urls) == 1
            created_path = UPLOAD_DIR / Path(urls[0]).name
            assert created_path.is_file()

        token = csrf_token(admin_client.get(f"/admin/posts/{post_id}/edit").text)
        response = admin_client.post(
            f"/admin/posts/{post_id}/edit",
            data={
                "csrf_token": token,
                "title": POST_TITLE,
                "summary": "pytest",
                "content": "## no image",
                "published_at": "2026-10-30",
                "tags": "pytest",
                "image_alt": "",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert not created_path.exists()

        token = csrf_token(admin_client.get(f"/admin/posts/{post_id}/edit").text)
        response = admin_client.post(
            f"/admin/posts/{post_id}/delete",
            data={"csrf_token": token},
            follow_redirects=False,
        )
        assert response.status_code == 303
        with SessionLocal() as db:
            assert db.get(BlogPost, post_id) is None
    finally:
        _cleanup_content()
        if created_path and created_path.exists():
            created_path.unlink()


def test_edit_without_csrf_rejected(admin_client):
    _cleanup_content()
    try:
        token = csrf_token(admin_client.get("/admin/posts/new").text)
        response = admin_client.post(
            "/admin/posts/new",
            data={
                "csrf_token": token,
                "title": POST_TITLE,
                "summary": "pytest",
                "content": "## pytest",
                "published_at": "2026-10-30",
                "tags": "pytest",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303

        with SessionLocal() as db:
            post_id = db.scalar(select(BlogPost.id).where(BlogPost.title == POST_TITLE))

        response = admin_client.post(
            f"/admin/posts/{post_id}/edit",
            data={
                "title": POST_TITLE,
                "summary": "pytest",
                "content": "## no csrf",
                "published_at": "2026-10-30",
                "tags": "pytest",
            },
            follow_redirects=False,
        )
        assert response.status_code == 422
    finally:
        _cleanup_content()


def test_logout_requires_csrf(admin_client):
    token = csrf_token(admin_client.get("/admin/").text)

    missing = admin_client.post("/admin/logout", data={}, follow_redirects=False)
    assert missing.status_code == 422

    response = admin_client.post(
        "/admin/logout",
        data={"csrf_token": token},
        follow_redirects=False,
    )
    assert response.status_code == 303


def test_login_rate_limit(client):
    token = csrf_token(client.get("/admin/login").text)

    for _ in range(5):
        response = client.post(
            "/admin/login",
            data={
                "username": "nobody",
                "password": "wrong",
                "csrf_token": token,
            },
            follow_redirects=False,
        )
        assert response.status_code == 400

    response = client.post(
        "/admin/login",
        data={
            "username": "nobody",
            "password": "wrong",
            "csrf_token": token,
        },
        follow_redirects=False,
    )
    assert response.status_code == 429
    assert response.headers["retry-after"] == "300"


def test_post_title_and_summary_length_validation(admin_client):
    _cleanup_content()
    long_title = "x" * 201
    long_summary = "y" * 501
    try:
        token = csrf_token(admin_client.get("/admin/posts/new").text)
        response = admin_client.post(
            "/admin/posts/new",
            data={
                "csrf_token": token,
                "title": long_title,
                "summary": "pytest",
                "content": "正文",
                "published_at": "2026-10-30",
                "tags": "",
            },
            follow_redirects=False,
        )
        assert response.status_code == 400
        assert "标题" in response.text
        with SessionLocal() as db:
            assert (
                db.scalar(select(BlogPost).where(BlogPost.title == long_title)) is None
            )

        token = csrf_token(admin_client.get("/admin/posts/new").text)
        response = admin_client.post(
            "/admin/posts/new",
            data={
                "csrf_token": token,
                "title": POST_TITLE,
                "summary": long_summary,
                "content": "正文",
                "published_at": "2026-10-30",
                "tags": "",
            },
            follow_redirects=False,
        )
        assert response.status_code == 400
        assert "摘要" in response.text
    finally:
        _cleanup_content()
