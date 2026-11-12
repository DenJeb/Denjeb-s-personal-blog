from datetime import timedelta

from app.db import SessionLocal
from app.models import BlogPost
from app.time_utils import site_today


def _create_draft() -> int:
    with SessionLocal() as db:
        post = BlogPost(
            title="Draft Preview",
            slug="draft-preview",
            content="# 标题\n\n正文内容",
            published_at=site_today(),
            is_published=False,
        )
        db.add(post)
        db.commit()
        db.refresh(post)
        return post.id


def _delete_post(post_id: int) -> None:
    with SessionLocal() as db:
        post = db.get(BlogPost, post_id)
        if post is not None:
            db.delete(post)
            db.commit()


def test_admin_preview_requires_login(client):
    response = client.get("/admin/posts/1/preview", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/admin/login"


def test_admin_preview_renders_draft(admin_client):
    post_id = _create_draft()
    try:
        response = admin_client.get(f"/admin/posts/{post_id}/preview")
        assert response.status_code == 200
        assert "Draft Preview" in response.text
        assert "正文内容" in response.text
    finally:
        _delete_post(post_id)


def test_admin_preview_labels_future_post(admin_client):
    with SessionLocal() as db:
        post = BlogPost(
            title="Future Preview",
            slug="future-preview",
            content="# 未来\n\n正文",
            published_at=site_today() + timedelta(days=1),
            is_published=True,
        )
        db.add(post)
        db.commit()
        db.refresh(post)
        post_id = post.id

    try:
        response = admin_client.get(f"/admin/posts/{post_id}/preview")
        assert response.status_code == 200
        assert "Future Preview" in response.text
        assert "未到日期" in response.text
        assert "已发布" not in response.text
    finally:
        _delete_post(post_id)
