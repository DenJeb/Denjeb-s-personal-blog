from app.db import SessionLocal
from app.models import BlogPost
from app.time_utils import site_today
from tests.conftest import ADMIN_EMAIL, ADMIN_USERNAME

DRAFT_TITLE = "__pytest_admin_api_draft__"
DRAFT_SLUG = "__pytest_admin_api_draft__"


def _create_draft() -> int:
    with SessionLocal() as db:
        post = BlogPost(
            title=DRAFT_TITLE,
            slug=DRAFT_SLUG,
            summary="draft summary",
            content="# Draft\n\nbody",
            published_at=site_today(),
            is_published=False,
        )
        db.add(post)
        db.commit()
        db.refresh(post)
        return post.id


def test_admin_logout(admin_client):
    csrf = admin_client.get("/api/v1/auth/csrf").json()["csrf_token"]
    response = admin_client.post(
        "/api/v1/admin/logout",
        headers={"X-CSRF-Token": csrf},
    )

    assert response.status_code == 200
    assert admin_client.get("/api/v1/admin/me").status_code == 401


def _delete_draft(post_id: int) -> None:
    with SessionLocal() as db:
        post = db.get(BlogPost, post_id)
        if post is not None:
            db.delete(post)
            db.commit()


def test_admin_api_requires_login(client):
    assert client.get("/api/v1/admin/me").status_code == 401
    assert client.get("/api/v1/admin/dashboard").status_code == 401
    assert client.get("/api/v1/admin/posts").status_code == 401
    assert client.get("/api/v1/admin/posts/1").status_code == 401


def test_admin_api_rejects_frontend_user(user_client):
    assert user_client.get("/api/v1/admin/me").status_code == 401


def test_admin_me(admin_client):
    response = admin_client.get("/api/v1/admin/me")
    assert response.status_code == 200
    assert response.json() == {
        "username": ADMIN_USERNAME,
        "email": ADMIN_EMAIL,
    }


def test_admin_dashboard(admin_client):
    response = admin_client.get("/api/v1/admin/dashboard")
    assert response.status_code == 200
    data = response.json()
    for key in (
        "post_count",
        "moment_count",
        "message_count",
        "comment_count",
        "moment_comment_count",
        "user_count",
        "pending_count",
        "moment_pending_count",
    ):
        assert isinstance(data[key], int)


def test_admin_posts_include_drafts(admin_client):
    post_id = _create_draft()
    try:
        response = admin_client.get("/api/v1/admin/posts?page=1")
        assert response.status_code == 200
        items = response.json()["items"]
        draft = next(item for item in items if item["id"] == post_id)
        assert draft["title"] == DRAFT_TITLE
        assert draft["is_published"] is False
    finally:
        _delete_draft(post_id)


def test_admin_post_detail(admin_client):
    post_id = _create_draft()
    try:
        response = admin_client.get(f"/api/v1/admin/posts/{post_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == DRAFT_TITLE
        assert data["content"] == "# Draft\n\nbody"
        assert data["is_published"] is False
    finally:
        _delete_draft(post_id)

    assert admin_client.get("/api/v1/admin/posts/999999").status_code == 404
