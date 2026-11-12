"""
========== 旧 FastAPI 公开站点开关测试 ==========
"""

from app.config import settings


def test_legacy_public_site_can_be_disabled(client, monkeypatch):
    monkeypatch.setattr(settings, "legacy_public_site_enabled", False)

    assert client.get("/").status_code == 404
    assert client.get("/posts").status_code == 404
    assert client.get("/posts/1").status_code == 404
    assert client.get("/tags").status_code == 404

    # feed、API 和后台不受影响
    assert client.get("/rss.xml").status_code == 200
    assert client.get("/api/v1/posts").status_code == 200
    assert client.get("/healthz").status_code == 200
