"""
========== 公开页面测试 ==========
"""

import json
import re
import xml.etree.ElementTree as ET
from datetime import date
from urllib.parse import quote, urlparse

from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.db import SessionLocal
from app.main import app
from app.models import BlogPost


def test_public_pages(client):
    for path in (
        "/",
        "/posts",
        "/posts/1",
        "/tags",
        "/archive",
        "/search?q=FastAPI",
        "/about",
        "/moments",
        "/guestbook",
    ):
        response = client.get(path)
        assert response.status_code == 200, path

    assert "为什么用 FastAPI" in client.get("/posts/1").text


def test_legacy_post_id_redirects_to_public_slug(client):
    response = client.get("/posts/1", follow_redirects=False)
    assert response.status_code == 301
    location = response.headers["location"]
    assert urlparse(location).path.startswith("/posts/")
    assert "/api/" not in location


def test_rss_and_sitemap(client):
    rss = client.get("/rss.xml")
    assert rss.status_code == 200
    assert rss.headers["content-type"].startswith("application/rss+xml")
    assert ET.fromstring(rss.content).tag == "rss"

    sitemap = client.get("/sitemap.xml")
    assert sitemap.status_code == 200
    assert sitemap.headers["content-type"].startswith("application/xml")
    assert ET.fromstring(sitemap.content).tag.endswith("urlset")
    assert "/tags?tag=FastAPI" in sitemap.text

    full = client.get("/rss.xml?full=1")
    assert full.status_code == 200
    assert "content:encoded" in full.text
    item = ET.fromstring(full.content).find("channel/item")
    assert item is not None
    encoded = item.find("{http://purl.org/rss/1.0/modules/content/}encoded")
    assert encoded is not None
    assert "正文占位内容" in (encoded.text or "")


def test_404_page(client):
    response = client.get("/nope")
    assert response.status_code == 404
    assert "页面不存在" in response.text


def test_422_page(client):
    response = client.get("/posts?page=0")
    assert response.status_code == 422
    assert "请求参数不正确" in response.text
    assert response.headers["content-type"].startswith("text/html")


def test_bad_host_rejected():
    with TestClient(app, base_url="http://evil.com") as bad_client:
        assert bad_client.get("/").status_code == 400


def test_healthz(client):
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_security_headers(client):
    response = client.get("/")
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "strict-origin-when-cross-origin"
    assert "camera=()" in response.headers["permissions-policy"]
    csp = response.headers["content-security-policy"]
    assert "default-src 'self'" in csp
    assert "img-src 'self' data: https:" in csp

    login = client.get("/login")
    assert login.headers["cache-control"] == "no-store"


def test_theme_assets(client):
    assert client.get("/static/js/theme.js").status_code == 200
    css = client.get("/static/css/pygments.css")
    assert css.status_code == 200
    assert '[data-theme="dark"]' in css.text


def test_seo_meta(client):
    post = client.get("/posts/1").text
    assert '<meta name="description"' in post
    assert 'rel="canonical"' in post
    assert 'property="og:type" content="article"' in post
    assert 'property="og:title"' in post

    commented = client.get("/posts/1?comment=submitted").text
    canonical = re.search(r'rel="canonical" href="([^"]+)"', commented)
    assert canonical is not None
    assert "comment=" not in canonical.group(1)

    match = re.search(
        r'<script type="application/ld\+json"[^>]*>(.*?)</script>',
        post,
        re.DOTALL,
    )
    assert match is not None
    data = json.loads(match.group(1))
    assert data["@context"] == "https://schema.org"
    assert data["@type"] == "BlogPosting"
    assert data["headline"].startswith("博客开张")
    assert data["url"].endswith(
        "/posts/bo-ke-kai-zhang-wei-shi-yao-yong-fastapi-jinja2"
    )

    home = client.get("/").text
    assert 'property="og:type" content="website"' in home


def test_robots_and_favicon(client):
    robots = client.get("/robots.txt")
    assert robots.status_code == 200
    assert "Disallow: /admin/" in robots.text
    assert "Disallow: /login" in robots.text
    assert "Sitemap:" in robots.text

    favicon = client.get("/static/favicon.svg")
    assert favicon.status_code == 200
    assert "image/svg+xml" in favicon.headers["content-type"]


def test_search_wildcards_are_literal(client):
    response = client.get("/search?q=%25")
    assert response.status_code == 200
    assert "没有找到相关文章" in response.text


def test_tags_sorted_by_count_then_initial(client):
    text = client.get("/tags").text

    def position(tag: str) -> int:
        return text.index(f"/tags?tag={quote(tag, safe='')}")

    assert position("博客") < position("FastAPI") < position("学习")


def test_post_card_tags_sorted_by_initial(client):
    text = client.get("/posts").text
    card = re.search(r"<article>.*?</article>", text, re.DOTALL)
    assert card is not None
    card_text = card.group(0)

    def position(tag: str) -> int:
        return card_text.index(f"/tags?tag={quote(tag, safe='')}")

    assert position("博客") < position("FastAPI")


def test_tags_with_special_characters(client):
    with SessionLocal() as db:
        post = BlogPost(
            title="__pytest_special_tags__",
            summary="",
            content="特殊标签",
            content_html="<p>特殊标签</p>",
            published_at=date(2026, 1, 1),
            tags=["C/C++", "C#", "machine learning"],
        )
        db.add(post)
        db.commit()
        post_id = post.id

    try:
        home = client.get("/posts")
        assert home.status_code == 200
        assert "tag=C%2FC%2B%2B" in home.text

        for tag in ("C/C++", "C#", "machine learning"):
            response = client.get("/tags", params={"tag": tag})
            assert response.status_code == 200, tag
            assert tag in response.text

        sitemap = client.get("/sitemap.xml")
        assert sitemap.status_code == 200
        assert "tag=C%2FC%2B%2B" in sitemap.text
        assert "tag=C%23" in sitemap.text
    finally:
        with SessionLocal() as db:
            db.execute(delete(BlogPost).where(BlogPost.id == post_id))
            db.commit()
