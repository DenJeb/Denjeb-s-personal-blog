"""
========== 错误响应与缓存头测试 ==========
"""


def test_html_csrf_error_renders_html(client):
    response = client.post(
        "/login",
        data={
            "csrf_token": "bad-token",
            "email": "nobody@example.com",
            "password": "wrong",
        },
    )

    assert response.status_code == 400
    assert response.headers["content-type"].startswith("text/html")
    assert "CSRF" in response.text


def test_api_csrf_error_remains_json(client):
    response = client.post(
        "/api/v1/auth/login",
        headers={"X-CSRF-Token": "bad-token"},
        json={"email": "nobody@example.com", "password": "wrong"},
    )

    assert response.status_code == 400
    assert response.headers["content-type"].startswith("application/json")


def test_auth_and_admin_api_disable_cache(client):
    assert client.get("/api/v1/auth/me").headers["cache-control"] == "no-store"
    assert client.get("/api/v1/admin/me").headers["cache-control"] == "no-store"
