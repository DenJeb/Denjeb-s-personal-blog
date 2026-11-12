"""后台写接口测试：评论审核、内容管理、用户与安全设置。"""

import time
from uuid import uuid4

import pyotp
import pytest
from sqlalchemy import select

from app.db import SessionLocal
from app.models import (
    AdminUser,
    BlogPost,
    Comment,
    Message,
    Moment,
    MomentComment,
    User,
)
from app.services.uploads import UPLOAD_DIR
from app.time_utils import site_today
from tests.conftest import ADMIN_EMAIL, ADMIN_PASSWORD
from tests.utils import image_bytes

PNG = image_bytes()


def _csrf(client) -> str:
    return client.get("/api/v1/auth/csrf").json()["csrf_token"]


def _create_post_comment(approved: bool = False) -> tuple[int, int]:
    with SessionLocal() as db:
        post = BlogPost(
            title="__pytest_api_comment_post__",
            slug="__pytest_api_comment_post__",
            summary="summary",
            content="body",
            published_at=site_today(),
            is_published=True,
        )
        db.add(post)
        db.commit()
        db.refresh(post)

        comment = Comment(
            post_id=post.id,
            author_name="Alice",
            content="hello",
            is_approved=approved,
        )
        db.add(comment)
        db.commit()
        db.refresh(comment)
        return post.id, comment.id


def _delete_post(post_id: int) -> None:
    with SessionLocal() as db:
        post = db.get(BlogPost, post_id)
        if post is not None:
            db.delete(post)
            db.commit()


def _create_user() -> int:
    with SessionLocal() as db:
        user = User(
            email=f"__pytest_api_{uuid4().hex}@example.com",
            username=f"__pytest_api_{uuid4().hex[:10]}",
            password_hash="x",
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user.id


def _delete_user(user_id: int) -> None:
    with SessionLocal() as db:
        user = db.get(User, user_id)
        if user is not None:
            db.delete(user)
            db.commit()


def _create_message() -> int:
    with SessionLocal() as db:
        message = Message(author_name="Carol", content="hello")
        db.add(message)
        db.commit()
        db.refresh(message)
        return message.id


def _post_payload(**overrides) -> dict:
    payload = {
        "title": "__pytest_api_post__",
        "slug": "",
        "summary": "summary",
        "content": "# Hello\n\nbody",
        "published_at": site_today().isoformat(),
        "tags": ["Test", "Test", " Another "],
        "is_published": True,
    }
    payload.update(overrides)
    return payload


def _create_moment_comment() -> tuple[int, int]:
    with SessionLocal() as db:
        moment = Moment(content="__pytest_moment__")
        db.add(moment)
        db.commit()
        db.refresh(moment)

        comment = MomentComment(
            moment_id=moment.id,
            author_name="Bob",
            content="moment hello",
        )
        db.add(comment)
        db.commit()
        db.refresh(comment)
        return moment.id, comment.id


def test_admin_comment_api_requires_login(client):
    assert client.get("/api/v1/admin/comments").status_code == 401
    assert client.get("/api/v1/admin/moment-comments").status_code == 401


def test_admin_comment_api_rejects_missing_csrf(admin_client):
    post_id, comment_id = _create_post_comment()
    try:
        response = admin_client.post(f"/api/v1/admin/comments/{comment_id}/approve")
        assert response.status_code == 400
    finally:
        _delete_post(post_id)


def test_admin_comment_list_and_approve(admin_client):
    post_id, comment_id = _create_post_comment()
    try:
        response = admin_client.get("/api/v1/admin/comments")
        assert response.status_code == 200
        item = next(
            item for item in response.json()["items"] if item["id"] == comment_id
        )
        assert item["post_title"] == "__pytest_api_comment_post__"
        assert item["post_slug"] == "__pytest_api_comment_post__"
        assert item["is_approved"] is False

        response = admin_client.post(
            f"/api/v1/admin/comments/{comment_id}/approve",
            headers={"X-CSRF-Token": _csrf(admin_client)},
        )
        assert response.status_code == 200
        assert response.json()["is_approved"] is True

        with SessionLocal() as db:
            assert db.get(Comment, comment_id).is_approved is True
    finally:
        _delete_post(post_id)


def test_admin_comment_delete(admin_client):
    post_id, comment_id = _create_post_comment()
    try:
        response = admin_client.delete(
            f"/api/v1/admin/comments/{comment_id}",
            headers={"X-CSRF-Token": _csrf(admin_client)},
        )
        assert response.status_code == 204

        with SessionLocal() as db:
            assert db.get(Comment, comment_id) is None

        response = admin_client.delete(
            f"/api/v1/admin/comments/{comment_id}",
            headers={"X-CSRF-Token": _csrf(admin_client)},
        )
        assert response.status_code == 404
    finally:
        _delete_post(post_id)


def test_admin_moment_comment_list_and_toggle(admin_client):
    moment_id, comment_id = _create_moment_comment()

    response = admin_client.get("/api/v1/admin/moment-comments")
    assert response.status_code == 200
    item = next(item for item in response.json()["items"] if item["id"] == comment_id)
    assert item["moment_id"] == moment_id
    assert item["moment_page"] >= 1
    assert item["is_approved"] is False

    response = admin_client.post(
        f"/api/v1/admin/moment-comments/{comment_id}/approve",
        headers={"X-CSRF-Token": _csrf(admin_client)},
    )
    assert response.status_code == 200
    assert response.json()["is_approved"] is True

    response = admin_client.delete(
        f"/api/v1/admin/moment-comments/{comment_id}",
        headers={"X-CSRF-Token": _csrf(admin_client)},
    )
    assert response.status_code == 204


def test_admin_content_api_requires_login(client):
    assert client.get("/api/v1/admin/moments").status_code == 401
    assert client.get("/api/v1/admin/messages").status_code == 401
    assert client.get("/api/v1/admin/uploads").status_code == 401
    assert (
        client.post("/api/v1/admin/posts/preview", json={"content": "x"}).status_code
        == 401
    )


def test_admin_post_create_update_delete(admin_client):
    post_id = None
    try:
        response = admin_client.post(
            "/api/v1/admin/posts",
            json=_post_payload(),
            headers={"X-CSRF-Token": _csrf(admin_client)},
        )
        assert response.status_code == 201
        data = response.json()
        post_id = data["id"]
        assert data["title"] == "__pytest_api_post__"
        assert data["slug"] == "pytest-api-post"
        assert data["tags"] == ["Test", "Another"]
        assert data["content_html"]
        assert data["is_public"] is True

        response = admin_client.put(
            f"/api/v1/admin/posts/{post_id}",
            json=_post_payload(
                title="__pytest_api_post_updated__",
                slug="updated-slug",
                tags=["One"],
            ),
            headers={"X-CSRF-Token": _csrf(admin_client)},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "__pytest_api_post_updated__"
        assert data["slug"] == "updated-slug"
        assert data["tags"] == ["One"]

        response = admin_client.delete(
            f"/api/v1/admin/posts/{post_id}",
            headers={"X-CSRF-Token": _csrf(admin_client)},
        )
        assert response.status_code == 204
        assert admin_client.get(f"/api/v1/admin/posts/{post_id}").status_code == 404
        post_id = None
    finally:
        if post_id is not None:
            _delete_post(post_id)


def test_admin_post_write_validation(admin_client):
    csrf = _csrf(admin_client)

    response = admin_client.post(
        "/api/v1/admin/posts",
        json=_post_payload(title="   "),
        headers={"X-CSRF-Token": csrf},
    )
    assert response.status_code == 400

    response = admin_client.post(
        "/api/v1/admin/posts",
        json=_post_payload(content=""),
        headers={"X-CSRF-Token": csrf},
    )
    assert response.status_code == 422

    response = admin_client.post(
        "/api/v1/admin/posts",
        json=_post_payload(published_at="not-a-date"),
        headers={"X-CSRF-Token": csrf},
    )
    assert response.status_code == 422


def test_admin_post_slug_collision(admin_client):
    csrf = _csrf(admin_client)
    first_id = None
    second_id = None
    try:
        response = admin_client.post(
            "/api/v1/admin/posts",
            json=_post_payload(slug="dup-slug"),
            headers={"X-CSRF-Token": csrf},
        )
        assert response.status_code == 201
        first_id = response.json()["id"]
        assert response.json()["slug"] == "dup-slug"

        response = admin_client.post(
            "/api/v1/admin/posts",
            json=_post_payload(slug="dup-slug"),
            headers={"X-CSRF-Token": _csrf(admin_client)},
        )
        assert response.status_code == 201
        second_id = response.json()["id"]
        assert response.json()["slug"] == "dup-slug-2"
    finally:
        if first_id is not None:
            _delete_post(first_id)
        if second_id is not None:
            _delete_post(second_id)


def test_admin_post_tags_split_full_width_comma(admin_client):
    post_id = None
    try:
        response = admin_client.post(
            "/api/v1/admin/posts",
            json=_post_payload(
                slug=f"tags-{uuid4().hex}",
                tags=["FastAPI，博客", " Next.js "],
            ),
            headers={"X-CSRF-Token": _csrf(admin_client)},
        )
        assert response.status_code == 201
        post_id = response.json()["id"]
        assert response.json()["tags"] == ["FastAPI", "博客", "Next.js"]
    finally:
        if post_id is not None:
            _delete_post(post_id)


def test_admin_post_preview(admin_client):
    response = admin_client.post(
        "/api/v1/admin/posts/preview",
        json={"content": "# Hi\n\nbody"},
        headers={"X-CSRF-Token": _csrf(admin_client)},
    )
    assert response.status_code == 200
    assert "<h1" in response.json()["html"]


def test_admin_upload_inline_list_and_delete(admin_client):
    csrf = _csrf(admin_client)
    response = admin_client.post(
        "/api/v1/admin/uploads/inline",
        files={"image": ("test.png", PNG, "image/png")},
        data={"image_alt": "Cover"},
        headers={"X-CSRF-Token": csrf},
    )
    assert response.status_code == 200
    data = response.json()
    name = data["url"].removeprefix("/static/uploads/")
    path = UPLOAD_DIR / name
    assert path.exists()
    assert "![Cover]" in data["markdown"]

    try:
        response = admin_client.get("/api/v1/admin/uploads")
        assert response.status_code == 200
        item = next(item for item in response.json()["items"] if item["name"] == name)
        assert item["referenced"] is False

        response = admin_client.post(
            "/api/v1/admin/uploads/delete",
            json={"path": name},
            headers={"X-CSRF-Token": _csrf(admin_client)},
        )
        assert response.status_code == 200
        assert not path.exists()
    finally:
        if path.exists():
            path.unlink()


def test_admin_upload_delete_rejects_traversal(admin_client):
    response = admin_client.post(
        "/api/v1/admin/uploads/delete",
        json={"path": "../x.png"},
        headers={"X-CSRF-Token": _csrf(admin_client)},
    )
    assert response.status_code == 400


def test_admin_upload_in_use_is_protected(admin_client):
    name = f"__pytest_ref_{uuid4().hex}.png"
    path = UPLOAD_DIR / name
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    path.write_bytes(PNG)

    csrf = _csrf(admin_client)
    post_id = None
    try:
        response = admin_client.post(
            "/api/v1/admin/posts",
            json=_post_payload(
                content=f"![x](/static/uploads/{name})",
                slug=f"ref-{uuid4().hex}",
            ),
            headers={"X-CSRF-Token": csrf},
        )
        assert response.status_code == 201
        post_id = response.json()["id"]

        response = admin_client.post(
            "/api/v1/admin/uploads/delete",
            json={"path": name},
            headers={"X-CSRF-Token": _csrf(admin_client)},
        )
        assert response.status_code == 409
        assert path.exists()
    finally:
        if post_id is not None:
            _delete_post(post_id)
        if path.exists():
            path.unlink()


def test_admin_post_delete_cleans_uploads(admin_client):
    name = f"__pytest_clean_{uuid4().hex}.png"
    path = UPLOAD_DIR / name
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    path.write_bytes(PNG)

    response = admin_client.post(
        "/api/v1/admin/posts",
        json=_post_payload(
            content=f"![x](/static/uploads/{name})",
            slug=f"clean-{uuid4().hex}",
        ),
        headers={"X-CSRF-Token": _csrf(admin_client)},
    )
    assert response.status_code == 201
    post_id = response.json()["id"]

    response = admin_client.delete(
        f"/api/v1/admin/posts/{post_id}",
        headers={"X-CSRF-Token": _csrf(admin_client)},
    )
    assert response.status_code == 204
    assert not path.exists()


def test_admin_post_delete_keeps_shared_upload(admin_client):
    name = f"__pytest_shared_{uuid4().hex}.png"
    path = UPLOAD_DIR / name
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    path.write_bytes(PNG)

    post_ids: list[int] = []
    try:
        for suffix in ("a", "b"):
            response = admin_client.post(
                "/api/v1/admin/posts",
                json=_post_payload(
                    content=f"![x](/static/uploads/{name})",
                    slug=f"shared-{suffix}-{uuid4().hex}",
                ),
                headers={"X-CSRF-Token": _csrf(admin_client)},
            )
            assert response.status_code == 201
            post_ids.append(response.json()["id"])

        response = admin_client.delete(
            f"/api/v1/admin/posts/{post_ids[0]}",
            headers={"X-CSRF-Token": _csrf(admin_client)},
        )
        assert response.status_code == 204
        assert path.exists()

        response = admin_client.delete(
            f"/api/v1/admin/posts/{post_ids[1]}",
            headers={"X-CSRF-Token": _csrf(admin_client)},
        )
        assert response.status_code == 204
        assert not path.exists()
        post_ids = []
    finally:
        for post_id in post_ids:
            _delete_post(post_id)
        if path.exists():
            path.unlink()


def test_admin_moment_detail(admin_client):
    response = admin_client.post(
        "/api/v1/admin/moments",
        json={"content": "__pytest_api_moment_detail__"},
        headers={"X-CSRF-Token": _csrf(admin_client)},
    )
    assert response.status_code == 201
    moment_id = response.json()["id"]

    response = admin_client.get(f"/api/v1/admin/moments/{moment_id}")
    assert response.status_code == 200
    assert response.json()["content"] == "__pytest_api_moment_detail__"
    assert response.json()["public_page"] >= 1

    assert admin_client.get("/api/v1/admin/moments/999999").status_code == 404


def test_admin_moment_crud(admin_client):
    response = admin_client.post(
        "/api/v1/admin/moments",
        json={"content": "__pytest_api_moment__"},
        headers={"X-CSRF-Token": _csrf(admin_client)},
    )
    assert response.status_code == 201
    moment_id = response.json()["id"]

    response = admin_client.get("/api/v1/admin/moments")
    assert response.status_code == 200
    assert any(item["id"] == moment_id for item in response.json()["items"])

    response = admin_client.put(
        f"/api/v1/admin/moments/{moment_id}",
        json={"content": "__pytest_api_moment_updated__"},
        headers={"X-CSRF-Token": _csrf(admin_client)},
    )
    assert response.status_code == 200
    assert response.json()["content"] == "__pytest_api_moment_updated__"

    response = admin_client.delete(
        f"/api/v1/admin/moments/{moment_id}",
        headers={"X-CSRF-Token": _csrf(admin_client)},
    )
    assert response.status_code == 204


def test_admin_message_list_and_delete(admin_client):
    message_id = _create_message()

    response = admin_client.get("/api/v1/admin/messages")
    assert response.status_code == 200
    assert any(item["id"] == message_id for item in response.json()["items"])

    response = admin_client.delete(
        f"/api/v1/admin/messages/{message_id}",
        headers={"X-CSRF-Token": _csrf(admin_client)},
    )
    assert response.status_code == 204

    with SessionLocal() as db:
        assert db.get(Message, message_id) is None


def test_admin_users_api_requires_login(client):
    assert client.get("/api/v1/admin/users").status_code == 401
    assert client.get("/api/v1/admin/security").status_code == 401


def test_admin_user_list_toggle_delete(admin_client):
    user_id: int | None = _create_user()
    try:
        response = admin_client.get("/api/v1/admin/users")
        assert response.status_code == 200
        item = next(item for item in response.json()["items"] if item["id"] == user_id)
        assert item["is_active"] is True

        response = admin_client.post(
            f"/api/v1/admin/users/{user_id}/toggle",
            headers={"X-CSRF-Token": _csrf(admin_client)},
        )
        assert response.status_code == 200
        assert response.json()["is_active"] is False

        with SessionLocal() as db:
            assert db.get(User, user_id).is_active is False

        response = admin_client.post(
            f"/api/v1/admin/users/{user_id}/toggle",
            headers={"X-CSRF-Token": _csrf(admin_client)},
        )
        assert response.status_code == 200
        assert response.json()["is_active"] is True

        response = admin_client.delete(
            f"/api/v1/admin/users/{user_id}",
            headers={"X-CSRF-Token": _csrf(admin_client)},
        )
        assert response.status_code == 204

        with SessionLocal() as db:
            assert db.get(User, user_id) is None
        user_id = None
    finally:
        if user_id is not None:
            _delete_user(user_id)


def test_admin_security_start_requires_csrf(admin_client):
    response = admin_client.post("/api/v1/admin/security/totp/start")
    assert response.status_code == 400


def test_admin_security_totp_flow(admin_client):
    response = admin_client.get("/api/v1/admin/security")
    assert response.status_code == 200
    assert response.json()["totp_enabled"] is False
    assert response.json()["setup_secret"] is None

    response = admin_client.post(
        "/api/v1/admin/security/totp/start",
        headers={"X-CSRF-Token": _csrf(admin_client)},
    )
    assert response.status_code == 200
    secret = response.json()["setup_secret"]
    assert secret
    assert response.json()["setup_uri"].startswith("otpauth://")

    response = admin_client.post(
        "/api/v1/admin/security/totp/enable",
        json={"code": pyotp.TOTP(secret).now()},
        headers={"X-CSRF-Token": _csrf(admin_client)},
    )
    assert response.status_code == 200

    response = admin_client.get("/api/v1/admin/security")
    assert response.json()["totp_enabled"] is True

    with SessionLocal() as db:
        admin = db.scalar(select(AdminUser).where(AdminUser.email == ADMIN_EMAIL))
        before_version = admin.session_version

    response = admin_client.post(
        "/api/v1/admin/security/totp/disable",
        json={"password": "wrong-password", "code": pyotp.TOTP(secret).now()},
        headers={"X-CSRF-Token": _csrf(admin_client)},
    )
    assert response.status_code == 400

    response = admin_client.post(
        "/api/v1/admin/security/totp/disable",
        json={"password": ADMIN_PASSWORD, "code": pyotp.TOTP(secret).now()},
        headers={"X-CSRF-Token": _csrf(admin_client)},
    )
    assert response.status_code == 200

    with SessionLocal() as db:
        admin = db.scalar(select(AdminUser).where(AdminUser.email == ADMIN_EMAIL))
        assert admin.session_version == before_version + 1

    response = admin_client.get("/api/v1/admin/security")
    assert response.json()["totp_enabled"] is False
    assert admin_client.get("/api/v1/admin/me").status_code == 200


def test_admin_totp_enable_rejects_bad_code(admin_client):
    response = admin_client.post(
        "/api/v1/admin/security/totp/start",
        headers={"X-CSRF-Token": _csrf(admin_client)},
    )
    assert response.status_code == 200
    secret = response.json()["setup_secret"]

    response = admin_client.post(
        "/api/v1/admin/security/totp/enable",
        json={"code": pyotp.TOTP(secret).at(time.time() + 3600)},
        headers={"X-CSRF-Token": _csrf(admin_client)},
    )
    assert response.status_code == 400

    response = admin_client.get("/api/v1/admin/security")
    assert response.json()["totp_enabled"] is False


CSRF_CASES = [
    ("POST", "/api/v1/admin/posts", _post_payload(), None),
    ("PUT", "/api/v1/admin/posts/1", _post_payload(), None),
    ("DELETE", "/api/v1/admin/posts/999999", None, None),
    ("POST", "/api/v1/admin/posts/preview", {"content": "x"}, None),
    ("POST", "/api/v1/admin/comments/999999/approve", None, None),
    ("DELETE", "/api/v1/admin/comments/999999", None, None),
    ("POST", "/api/v1/admin/moment-comments/999999/approve", None, None),
    ("DELETE", "/api/v1/admin/moment-comments/999999", None, None),
    ("POST", "/api/v1/admin/moments", {"content": "x"}, None),
    ("PUT", "/api/v1/admin/moments/999999", {"content": "x"}, None),
    ("DELETE", "/api/v1/admin/moments/999999", None, None),
    ("DELETE", "/api/v1/admin/messages/999999", None, None),
    ("POST", "/api/v1/admin/users/999999/toggle", None, None),
    ("DELETE", "/api/v1/admin/users/999999", None, None),
    ("POST", "/api/v1/admin/uploads/delete", {"path": "x"}, None),
    ("POST", "/api/v1/admin/security/totp/start", None, None),
    ("POST", "/api/v1/admin/security/totp/enable", {"code": "123456"}, None),
    (
        "POST",
        "/api/v1/admin/security/totp/disable",
        {"password": "x", "code": "123456"},
        None,
    ),
    (
        "POST",
        "/api/v1/admin/uploads/inline",
        None,
        {"image": ("x.png", PNG, "image/png")},
    ),
]


@pytest.mark.parametrize("method,path,payload,files", CSRF_CASES)
def test_admin_writes_require_csrf(admin_client, method, path, payload, files):
    kwargs = {}
    if payload is not None:
        kwargs["json"] = payload
    if files is not None:
        kwargs["files"] = files

    response = admin_client.request(method, path, **kwargs)
    assert response.status_code == 400
