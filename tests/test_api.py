"""
========== 公开 JSON API 测试 ==========
"""

from datetime import date
from uuid import uuid4

from sqlalchemy import delete

from app.db import SessionLocal
from app.markdown import render_markdown_with_toc
from app.models import BlogPost, Comment, Message, Moment, MomentComment

PREFIX = "__pytest_api_"


def _cleanup_posts() -> None:
    with SessionLocal() as db:
        db.execute(delete(BlogPost).where(BlogPost.title.like(PREFIX + "%")))
        db.commit()


def _add_post(
    title: str,
    slug: str,
    published_at: date,
    content: str = "正文",
    tags: list[str] | None = None,
    is_published: bool = True,
) -> int:
    html, _ = render_markdown_with_toc(content)
    with SessionLocal() as db:
        post = BlogPost(
            title=title,
            slug=slug,
            summary="",
            content=content,
            content_html=html,
            published_at=published_at,
            tags=tags or [],
            is_published=is_published,
        )
        db.add(post)
        db.commit()
        return post.id


def test_site_info(client):
    response = client.get("/api/v1/site")
    assert response.status_code == 200
    payload = response.json()
    assert payload["app_name"]
    assert payload["author"]
    assert payload["site_url"].startswith("http")


def test_posts_list_and_pagination(client):
    response = client.get("/api/v1/posts", params={"per_page": 1})
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["items"]) == 1
    assert payload["meta"]["per_page"] == 1
    assert payload["meta"]["total"] >= 2
    item = payload["items"][0]
    for key in ("id", "title", "slug", "url", "summary", "published_at", "tags"):
        assert key in item
    assert "content" not in item
    assert item["reading_minutes"] >= 1


def test_post_detail_by_slug_and_id(client):
    with SessionLocal() as db:
        post = db.get(BlogPost, 1)
        assert post is not None and post.slug
        slug = post.slug

    by_slug = client.get(f"/api/v1/posts/{slug}")
    assert by_slug.status_code == 200
    payload = by_slug.json()
    assert payload["slug"] == slug
    assert "updated_at" in payload
    assert payload["content"]
    assert payload["content_html"]
    assert isinstance(payload["toc"], list)
    assert "previous_post" in payload
    assert "next_post" in payload
    assert isinstance(payload["related_posts"], list)

    by_id = client.get("/api/v1/posts/1")
    assert by_id.status_code == 200
    assert by_id.json()["slug"] == slug


def test_post_detail_includes_toc_navigation_and_related(client):
    _cleanup_posts()
    tag = f"{PREFIX}tag_{uuid4().hex}"
    ids = []
    try:
        ids.append(
            _add_post(
                PREFIX + "old",
                f"{PREFIX}old",
                date(2026, 1, 1),
                content="# 旧标题\n\n正文",
                tags=[tag],
            )
        )
        ids.append(
            _add_post(
                PREFIX + "current",
                f"{PREFIX}current",
                date(2026, 2, 1),
                content="# 第一节\n\n## 小节\n\n正文",
                tags=[tag],
            )
        )
        ids.append(
            _add_post(
                PREFIX + "new",
                f"{PREFIX}new",
                date(2026, 3, 1),
                content="# 新标题\n\n正文",
                tags=[tag],
            )
        )

        response = client.get(f"/api/v1/posts/{PREFIX}current")
        assert response.status_code == 200
        payload = response.json()
        assert [item["id"] for item in payload["toc"]] == ["di-yi-jie", "xiao-jie"]
        assert payload["previous_post"]["title"] == PREFIX + "old"
        assert payload["next_post"]["title"] == PREFIX + "new"
        assert PREFIX + "old" in [item["title"] for item in payload["related_posts"]]
        assert PREFIX + "new" in [item["title"] for item in payload["related_posts"]]
    finally:
        with SessionLocal() as db:
            db.execute(delete(BlogPost).where(BlogPost.id.in_(ids)))
            db.commit()
        _cleanup_posts()


def test_draft_is_hidden_even_for_admin(client, admin_client):
    _cleanup_posts()
    try:
        post_id = _add_post(
            PREFIX + "draft",
            f"{PREFIX}draft",
            date(2026, 1, 1),
            is_published=False,
        )
        assert client.get(f"/api/v1/posts/{PREFIX}draft").status_code == 404
        assert admin_client.get(f"/api/v1/posts/{PREFIX}draft").status_code == 404
        listing = client.get("/api/v1/posts", params={"per_page": 50})
        assert PREFIX + "draft" not in [
            item["title"] for item in listing.json()["items"]
        ]
    finally:
        with SessionLocal() as db:
            db.execute(delete(BlogPost).where(BlogPost.id == post_id))
            db.commit()


def test_tags_and_tag_filter(client):
    response = client.get("/api/v1/tags")
    assert response.status_code == 200
    items = response.json()["items"]
    assert any(item["name"] == "FastAPI" for item in items)
    assert all(item["count"] >= 1 for item in items)

    filtered = client.get("/api/v1/posts", params={"tag": "FastAPI"})
    assert filtered.status_code == 200
    assert all("FastAPI" in item["tags"] for item in filtered.json()["items"])


def test_search_and_archive(client):
    search = client.get("/api/v1/search", params={"q": "FastAPI"})
    assert search.status_code == 200
    assert search.json()["meta"]["total"] >= 1

    wildcard = client.get("/api/v1/search", params={"q": "%"})
    assert wildcard.status_code == 200
    assert wildcard.json()["items"] == []

    archive = client.get("/api/v1/archive")
    assert archive.status_code == 200
    payload = archive.json()
    assert payload["total"] >= 2
    assert payload["years"]
    assert payload["years"][0]["months"][0]["posts"]


def test_comments_only_approved(client):
    with SessionLocal() as db:
        post = db.get(BlogPost, 1)
        assert post is not None and post.slug
        approved = Comment(
            post_id=post.id,
            author_name="__pytest_api_approved__",
            content=f"{PREFIX}approved",
            is_approved=True,
        )
        pending = Comment(
            post_id=post.id,
            author_name="__pytest_api_pending__",
            content=f"{PREFIX}pending",
            is_approved=False,
        )
        db.add_all([approved, pending])
        db.commit()
        approved_id, pending_id = approved.id, pending.id
        slug = post.slug

    try:
        response = client.get(f"/api/v1/posts/{slug}/comments")
        assert response.status_code == 200
        payload = response.json()
        assert payload["meta"]["total"] == 1
        assert payload["items"][0]["id"] == approved_id
        assert PREFIX + "pending" not in response.text
    finally:
        with SessionLocal() as db:
            db.execute(delete(Comment).where(Comment.id.in_([approved_id, pending_id])))
            db.commit()


def test_moments_include_only_approved_comments(client):
    with SessionLocal() as db:
        moment = Moment(content=f"{PREFIX}moment")
        db.add(moment)
        db.flush()
        db.add_all(
            [
                MomentComment(
                    moment_id=moment.id,
                    author_name="__pytest_api__",
                    content=f"{PREFIX}approved_moment_comment",
                    is_approved=True,
                ),
                MomentComment(
                    moment_id=moment.id,
                    author_name="__pytest_api__",
                    content=f"{PREFIX}pending_moment_comment",
                    is_approved=False,
                ),
            ]
        )
        db.commit()
        moment_id = moment.id

    response = client.get("/api/v1/moments", params={"per_page": 50})
    assert response.status_code == 200
    item = next(item for item in response.json()["items"] if item["id"] == moment_id)
    assert item["comment_count"] == 1
    assert len(item["comments"]) == 1
    assert PREFIX + "pending_moment_comment" not in response.text


def test_guestbook(client):
    with SessionLocal() as db:
        message = Message(
            user_id=None,
            author_name="__pytest_api__",
            content=f"{PREFIX}guestbook",
        )
        db.add(message)
        db.commit()
        message_id = message.id

    response = client.get("/api/v1/guestbook", params={"per_page": 50})
    assert response.status_code == 200
    assert any(
        item["id"] == message_id and item["content"] == f"{PREFIX}guestbook"
        for item in response.json()["items"]
    )


def test_recent_posts(client):
    response = client.get("/api/v1/recent", params={"limit": 1})
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_api_404_is_json(client):
    response = client.get("/api/v1/posts/nope")
    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/json")
    assert response.json()["detail"]


def test_api_validation_error_is_json(client):
    response = client.get("/api/v1/posts", params={"page": 0})
    assert response.status_code == 422
    assert response.headers["content-type"].startswith("application/json")
    assert response.json()["detail"] == "请求参数不正确"


def test_api_uses_disabled_email_setting():
    from app.config import settings

    assert settings.email_enabled is False
