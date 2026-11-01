"""
========== 文章公开可见性测试 ==========
"""

from datetime import date, timedelta

from sqlalchemy import delete

from app.db import SessionLocal
from app.models import BlogPost

FUTURE_TITLE = "__pytest_future_post__"
DRAFT_TITLE = "__pytest_draft_post__"
TAG = "__pytest_visibility__"


def _cleanup() -> None:
    with SessionLocal() as db:
        db.execute(
            delete(BlogPost).where(BlogPost.title.in_([FUTURE_TITLE, DRAFT_TITLE]))
        )
        db.commit()


def _create_post(title: str, published_at: date, is_published: bool) -> int:
    with SessionLocal() as db:
        post = BlogPost(
            title=title,
            summary="",
            content="正文",
            content_html="<p>正文</p>",
            published_at=published_at,
            tags=[TAG],
            is_published=is_published,
        )
        db.add(post)
        db.commit()
        return post.id


def _assert_hidden(client, admin_client, title: str, post_id: int) -> None:
    assert title not in client.get("/posts").text
    assert title not in client.get("/archive").text
    assert title not in client.get("/tags", params={"tag": TAG}).text
    search = client.get("/search", params={"q": title})
    assert f"/posts/{post_id}" not in search.text
    assert title not in client.get("/rss.xml?full=1").text
    assert f"/posts/{post_id}" not in client.get("/sitemap.xml").text
    assert client.get(f"/posts/{post_id}").status_code == 404

    assert title in admin_client.get("/admin/posts").text
    assert admin_client.get(f"/posts/{post_id}").status_code == 200


def test_future_post_is_hidden(client, admin_client):
    _cleanup()
    post_id = _create_post(
        FUTURE_TITLE,
        date.today() + timedelta(days=5),
        is_published=True,
    )
    try:
        _assert_hidden(client, admin_client, FUTURE_TITLE, post_id)
    finally:
        _cleanup()


def test_draft_post_is_hidden(client, admin_client):
    _cleanup()
    post_id = _create_post(
        DRAFT_TITLE,
        date.today() - timedelta(days=1),
        is_published=False,
    )
    try:
        _assert_hidden(client, admin_client, DRAFT_TITLE, post_id)
    finally:
        _cleanup()
