from tests.conftest import USER_EMAIL, USER_NICKNAME, USER_PASSWORD


def _csrf(client) -> str:
    response = client.get("/api/v1/auth/csrf")
    assert response.status_code == 200
    return response.json()["csrf_token"]


def test_auth_me_anonymous(client):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 200
    assert response.json() == {"user": None}


def test_auth_me_logged_in(user_client):
    response = user_client.get("/api/v1/auth/me")
    assert response.status_code == 200
    assert response.json() == {"user": {"name": USER_NICKNAME}}


def test_csrf_token_is_stable(user_client):
    assert _csrf(user_client) == _csrf(user_client)


def test_api_login_requires_csrf(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@example.com", "password": "whatever"},
    )
    assert response.status_code == 400


def test_api_login_logout_flow(user_client):
    token = _csrf(user_client)
    headers = {"X-CSRF-Token": token}

    response = user_client.post("/api/v1/auth/logout", headers=headers)
    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert user_client.get("/api/v1/auth/me").json() == {"user": None}

    response = user_client.post(
        "/api/v1/auth/login",
        headers=headers,
        json={"email": USER_EMAIL, "password": "wrong-password"},
    )
    assert response.status_code == 400

    response = user_client.post(
        "/api/v1/auth/login",
        headers=headers,
        json={"email": USER_EMAIL, "password": USER_PASSWORD},
    )
    assert response.status_code == 200
    assert response.json() == {"user": {"name": USER_NICKNAME}}
    assert user_client.get("/api/v1/auth/me").json() == {
        "user": {"name": USER_NICKNAME}
    }
