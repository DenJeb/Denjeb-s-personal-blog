"""
========== 标签和搜索分页测试 ==========
"""

from datetime import date

from sqlalchemy import delete

from app.db import SessionLocal
from app.models import BlogPost
from app.routers import public

TAG = "__pytest_tag__"
KEYWORD = "__pytest_keyword__"


def _cleanup_posts() -> None:
    with SessionLocal() as db:
        db.execute(delete(BlogPost).where(BlogPost.title.like("__pytest_page_%")))
        db.commit()


def test_tag_pagination(client, monkeypatch):
    _cleanup_posts()
    monkeypatch.setattr(public, "POSTS_PER_PAGE", 1)
    try:
        with SessionLocal() as db:
            for index in range(2):
                db.add(
                    BlogPost(
                        title=f"__pytest_page_tag_{index}",
                        summary="",
                        content="content",
                        published_at=date(2020, 1, index + 1),
                        tags=[TAG],
                    )
                )
            db.commit()

        first = client.get("/tags", params={"tag": TAG})
        assert "第 1 / 2 页" in first.text

        second = client.get("/tags", params={"tag": TAG, "page": 2})
        assert "第 2 / 2 页" in second.text

        last = client.get(
            "/tags", params={"tag": TAG, "page": 9}, follow_redirects=False
        )
        assert last.status_code == 303
        assert "page=2" in last.headers["location"]
    finally:
        _cleanup_posts()


def test_search_pagination(client, monkeypatch):
    _cleanup_posts()
    monkeypatch.setattr(public, "POSTS_PER_PAGE", 1)
    try:
        with SessionLocal() as db:
            for index in range(2):
                db.add(
                    BlogPost(
                        title=f"__pytest_page_search_{index}",
                        summary="",
                        content=f"unique {KEYWORD} content",
                        published_at=date(2020, 2, index + 1),
                        tags=[],
                    )
                )
            db.commit()

        first = client.get(f"/search?q={KEYWORD}")
        assert "第 1 / 2 页" in first.text

        second = client.get(f"/search?q={KEYWORD}&page=2")
        assert "第 2 / 2 页" in second.text

        last = client.get(f"/search?q={KEYWORD}&page=9", follow_redirects=False)
        assert last.status_code == 303
        assert "page=2" in last.headers["location"]
    finally:
        _cleanup_posts()
