"""
========== 后台编辑器接口测试 ==========
"""

from pathlib import Path

from app.services.uploads import UPLOAD_DIR
from tests.utils import csrf_token, image_bytes

PNG = image_bytes()


def test_preview_requires_admin(client):
    token = csrf_token(client.get("/admin/login").text)
    response = client.post(
        "/admin/posts/preview",
        data={"csrf_token": token, "content": "# hi"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/admin/login"


def test_preview_renders_markdown(admin_client):
    token = csrf_token(admin_client.get("/admin/posts/new").text)
    response = admin_client.post(
        "/admin/posts/preview",
        data={
            "csrf_token": token,
            "content": "# 标题\n\n**加粗**\n\n<script>alert(1)</script>",
        },
    )
    assert response.status_code == 200
    assert '<h1 id="biao-ti">标题</h1>' in response.text
    assert "<strong>加粗</strong>" in response.text
    assert "<script>" not in response.text
    assert "alert(1)" in response.text
    assert response.headers["cache-control"] == "no-store"


def test_preview_requires_csrf(admin_client):
    response = admin_client.post(
        "/admin/posts/preview",
        data={"content": "# hi"},
    )
    assert response.status_code == 422


def test_inline_upload_returns_markdown(admin_client):
    token = csrf_token(admin_client.get("/admin/posts/new").text)
    response = admin_client.post(
        "/admin/uploads/inline",
        data={"csrf_token": token, "image_alt": "截图"},
        files={"image": ("test.png", PNG, "image/png")},
    )
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"

    payload = response.json()
    assert payload["url"].startswith("/static/uploads/")
    assert payload["url"].endswith(".webp")
    assert payload["markdown"] == f"![截图]({payload['url']})"

    path = UPLOAD_DIR / Path(payload["url"]).name
    try:
        assert path.is_file()
    finally:
        path.unlink(missing_ok=True)


def test_inline_upload_rejects_non_image(admin_client):
    token = csrf_token(admin_client.get("/admin/posts/new").text)
    response = admin_client.post(
        "/admin/uploads/inline",
        data={"csrf_token": token},
        files={"image": ("x.txt", b"hello", "text/plain")},
    )
    assert response.status_code == 400
    assert "只支持" in response.json()["detail"]


def test_inline_upload_rejects_svg(admin_client):
    token = csrf_token(admin_client.get("/admin/posts/new").text)
    response = admin_client.post(
        "/admin/uploads/inline",
        data={"csrf_token": token},
        files={"image": ("x.svg", b"<svg></svg>", "image/svg+xml")},
    )
    assert response.status_code == 400


def test_inline_upload_requires_admin(client):
    token = csrf_token(client.get("/admin/login").text)
    response = client.post(
        "/admin/uploads/inline",
        data={"csrf_token": token},
        files={"image": ("test.png", PNG, "image/png")},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/admin/login"


def test_inline_upload_requires_csrf(admin_client):
    response = admin_client.post(
        "/admin/uploads/inline",
        files={"image": ("test.png", PNG, "image/png")},
    )
    assert response.status_code == 422
