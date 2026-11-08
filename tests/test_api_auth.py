from pwdlib import PasswordHash
from sqlalchemy import delete
from starlette.testclient import TestClient

from app.db import SessionLocal
from app.main import app
from app.models import RateLimitEvent, User
from tests.conftest import USER_EMAIL, USER_NICKNAME, USER_PASSWORD

INACTIVE_EMAIL = "__pytest_inactive_api@example.com"
INACTIVE_USERNAME = "__pytest_inactive_api__"


def _csrf(client) -> str:
    response = client.get("/api/v1/auth/csrf")
    assert response.status_code == 200
    return response.json()["csrf_token"]


def _cleanup_login_bucket(ip: str) -> None:
    with SessionLocal() as db:
        db.execute(
            delete(RateLimitEvent).where(RateLimitEvent.bucket == f"user_login:{ip}")
        )
        db.commit()


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

    # Logout invalidates the old CSRF token.
    token = _csrf(user_client)
    headers = {"X-CSRF-Token": token}

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


def test_api_login_rotates_csrf(user_client):
    old_token = _csrf(user_client)
    response = user_client.post(
        "/api/v1/auth/login",
        headers={"X-CSRF-Token": old_token},
        json={"email": USER_EMAIL, "password": USER_PASSWORD},
    )
    assert response.status_code == 200

    stale = user_client.post(
        "/api/v1/auth/logout",
        headers={"X-CSRF-Token": old_token},
    )
    assert stale.status_code == 400

    new_token = _csrf(user_client)
    assert new_token != old_token
    response = user_client.post(
        "/api/v1/auth/logout",
        headers={"X-CSRF-Token": new_token},
    )
    assert response.status_code == 200


def test_api_login_inactive_account():
    with SessionLocal() as db:
        db.execute(delete(User).where(User.email == INACTIVE_EMAIL))
        db.execute(delete(User).where(User.username == INACTIVE_USERNAME))
        db.add(
            User(
                email=INACTIVE_EMAIL,
                username=INACTIVE_USERNAME,
                password_hash=PasswordHash.recommended().hash("inactive-pass"),
                is_active=False,
            )
        )
        db.commit()

    try:
        with TestClient(app, client=("203.0.113.55", 50001)) as isolated:
            token = _csrf(isolated)
            response = isolated.post(
                "/api/v1/auth/login",
                headers={"X-CSRF-Token": token},
                json={
                    "email": INACTIVE_EMAIL,
                    "password": "inactive-pass",
                },
            )
            assert response.status_code == 403
    finally:
        with SessionLocal() as db:
            db.execute(delete(User).where(User.email == INACTIVE_EMAIL))
            db.execute(delete(User).where(User.username == INACTIVE_USERNAME))
            db.commit()


def test_api_login_rate_limit():
    ip = "203.0.113.66"
    _cleanup_login_bucket(ip)
    try:
        with TestClient(app, client=(ip, 50002)) as isolated:
            token = _csrf(isolated)
            headers = {"X-CSRF-Token": token}
            for _ in range(5):
                response = isolated.post(
                    "/api/v1/auth/login",
                    headers=headers,
                    json={
                        "email": "nobody@example.com",
                        "password": "wrong-password",
                    },
                )
                assert response.status_code == 400

            blocked = isolated.post(
                "/api/v1/auth/login",
                headers=headers,
                json={
                    "email": "nobody@example.com",
                    "password": "wrong-password",
                },
            )
            assert blocked.status_code == 429
            assert "尝试次数过多" in blocked.json()["detail"]
    finally:
        _cleanup_login_bucket(ip)
