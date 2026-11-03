"""
========== 阅读体验测试：slug、目录、相邻文章、相关文章 ==========
"""

from datetime import date
from uuid import uuid4

from sqlalchemy import delete, select

from app.db import SessionLocal
from app.markdown import render_markdown, render_markdown_with_toc
from app.models import BlogPost
from app.services.content import reading_minutes
from tests.utils import csrf_token

PREFIX = "__pytest_reading_"


def _cleanup() -> None:
    with SessionLocal() as db:
        db.execute(delete(BlogPost).where(BlogPost.title.like(PREFIX + "%")))
        db.commit()


def _add_post(
    title: str,
    slug: str,
    published_at: date,
    content: str = "正文",
    tags: list[str] | None = None,
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
        )
        db.add(post)
        db.commit()
        return post.id


def test_old_id_redirects_to_slug(client):
    with SessionLocal() as db:
        post = db.get(BlogPost, 1)
        assert post is not None and post.slug
        slug = post.slug

    response = client.get("/posts/1", follow_redirects=False)
    assert response.status_code == 301
    assert response.headers["location"].endswith(f"/posts/{slug}")


def test_slug_is_generated_from_chinese_title(admin_client):
    _cleanup()
    title = PREFIX + "中文标题"
    try:
        token = csrf_token(admin_client.get("/admin/posts/new").text)
        response = admin_client.post(
            "/admin/posts/new",
            data={
                "csrf_token": token,
                "title": title,
                "slug": "",
                "summary": "",
                "content": "正文",
                "published_at": "2026-11-03",
                "tags": "",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303

        with SessionLocal() as db:
            post = db.scalar(select(BlogPost).where(BlogPost.title == title))
            assert post is not None
            assert post.slug.startswith("pytest-reading-zhong-wen-biao-ti")
            post_id = post.id

        page = admin_client.get(f"/posts/{post_id}", follow_redirects=False)
        assert page.status_code == 301
        assert page.headers["location"].endswith(f"/posts/{post.slug}")
    finally:
        _cleanup()


def test_toc_adjacent_and_related_posts(client):
    _cleanup()
    tag = f"__pytest_tag_{uuid4().hex}__"
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
                content="# 第一节\n\n## 小节\n\n正文\n\n## 小节",
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

        page = client.get(f"/posts/{PREFIX}current")
        assert page.status_code == 200
        assert 'class="post-toc"' in page.text
        assert 'href="#di-yi-jie"' in page.text
        assert 'href="#xiao-jie"' in page.text
        assert 'href="#xiao-jie-2"' in page.text
        assert PREFIX + "old" in page.text
        assert PREFIX + "new" in page.text
        assert "相关文章" in page.text
        assert "约 1 分钟" in page.text
    finally:
        with SessionLocal() as db:
            db.execute(delete(BlogPost).where(BlogPost.id.in_(ids)))
            db.commit()
        _cleanup()


def test_markdown_heading_ids_and_lazy_images():
    html, toc = render_markdown_with_toc(
        "# 标题\n\n## 子标题\n\n# 标题\n\n![图](/static/uploads/a.png)"
    )
    assert [item["id"] for item in toc] == ["biao-ti", "zi-biao-ti", "biao-ti-2"]
    assert 'id="biao-ti"' in html
    assert 'loading="lazy"' in html
    assert render_markdown("# 标题").startswith('<h1 id="biao-ti">')


def test_reading_minutes():
    assert reading_minutes("中" * 800) == 2
    assert reading_minutes("hello " * 200) == 1
