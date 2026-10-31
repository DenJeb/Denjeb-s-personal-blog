"""
========== 前台邮箱账号测试 ==========
"""

import base64
import json
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from pwdlib import PasswordHash
from sqlalchemy import delete, select

from app.db import SessionLocal
from app.main import app
from app.models import EmailRegistrationBlock, User, VerificationCode
from app.routers import account as account_router
from tests.utils import csrf_token

EMAIL = "__pytest_account@example.com"
NICKNAME = "__pytest_account__"
PASSWORD = "AccountPass123!"
NEW_PASSWORD = "NewAccountPass123!"


def _cleanup_user() -> None:
    with SessionLocal() as db:
        db.execute(delete(User).where(User.email == EMAIL))
        db.execute(delete(User).where(User.username == NICKNAME))
        db.commit()


def _create_user(password: str = PASSWORD) -> None:
    with SessionLocal() as db:
        db.add(
            User(
                email=EMAIL,
                username=NICKNAME,
                password_hash=PasswordHash.recommended().hash(password),
            )
        )
        db.commit()


def _register_and_verify(client, monkeypatch, password: str = PASSWORD) -> None:
    monkeypatch.setattr(account_router, "_generate_code", lambda: "123456")
    monkeypatch.setattr(account_router, "send_code", lambda *args, **kwargs: True)

    token = csrf_token(client.get("/register").text)
    response = client.post(
        "/register",
        data={
            "csrf_token": token,
            "email": EMAIL,
            "nickname": NICKNAME,
            "password": password,
            "confirm": password,
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/register/verify"

    token = csrf_token(client.get("/register/verify").text)
    response = client.post(
        "/register/verify",
        data={"csrf_token": token, "code": "123456"},
        follow_redirects=False,
    )
    assert response.status_code == 303


def test_register_verify_login_logout(client, monkeypatch):
    _cleanup_user()
    try:
        _register_and_verify(client, monkeypatch)

        with SessionLocal() as db:
            user = db.scalar(select(User).where(User.email == EMAIL))
            assert user is not None
            assert user.username == NICKNAME

        assert NICKNAME in client.get("/").text

        token = csrf_token(client.get("/").text)
        response = client.post(
            "/logout",
            data={"csrf_token": token},
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert NICKNAME not in client.get("/").text

        token = csrf_token(client.get("/login").text)
        response = client.post(
            "/login",
            data={
                "csrf_token": token,
                "email": EMAIL,
                "password": PASSWORD,
            },
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert NICKNAME in client.get("/").text
    finally:
        _cleanup_user()


def test_register_duplicate_email(client):
    _cleanup_user()
    try:
        _create_user()

        token = csrf_token(client.get("/register").text)
        response = client.post(
            "/register",
            data={
                "csrf_token": token,
                "email": EMAIL,
                "nickname": "__another_nickname__",
                "password": PASSWORD,
                "confirm": PASSWORD,
            },
            follow_redirects=False,
        )
        assert response.status_code == 400
        assert "邮箱已被使用" in response.text
    finally:
        _cleanup_user()


def test_register_wrong_code(client, monkeypatch):
    _cleanup_user()
    try:
        monkeypatch.setattr(account_router, "_generate_code", lambda: "123456")
        monkeypatch.setattr(account_router, "send_code", lambda *args, **kwargs: True)

        token = csrf_token(client.get("/register").text)
        response = client.post(
            "/register",
            data={
                "csrf_token": token,
                "email": EMAIL,
                "nickname": NICKNAME,
                "password": PASSWORD,
                "confirm": PASSWORD,
            },
            follow_redirects=False,
        )
        assert response.status_code == 303

        token = csrf_token(client.get("/register/verify").text)
        response = client.post(
            "/register/verify",
            data={"csrf_token": token, "code": "000000"},
            follow_redirects=False,
        )
        assert response.status_code == 400
        with SessionLocal() as db:
            assert db.scalar(select(User).where(User.email == EMAIL)) is None
    finally:
        _cleanup_user()


def test_register_resend(client, monkeypatch):
    _cleanup_user()
    try:
        monkeypatch.setattr(account_router, "_generate_code", lambda: "123456")
        calls = []
        monkeypatch.setattr(
            account_router,
            "send_code",
            lambda *args, **kwargs: calls.append(args) or True,
        )

        token = csrf_token(client.get("/register").text)
        response = client.post(
            "/register",
            data={
                "csrf_token": token,
                "email": EMAIL,
                "nickname": NICKNAME,
                "password": PASSWORD,
                "confirm": PASSWORD,
            },
            follow_redirects=False,
        )
        assert response.status_code == 303

        token = csrf_token(client.get("/register/verify").text)
        response = client.post(
            "/register/resend",
            data={"csrf_token": token},
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert response.headers["location"] == "/register/verify?resent=1"
        assert len(calls) == 2

        token = csrf_token(client.get("/register/verify?resent=1").text)
        response = client.post(
            "/register/verify",
            data={"csrf_token": token, "code": "123456"},
            follow_redirects=False,
        )
        assert response.status_code == 303
        with SessionLocal() as db:
            assert db.scalar(select(User).where(User.email == EMAIL)) is not None
    finally:
        _cleanup_user()


def test_code_login(client, monkeypatch):
    _cleanup_user()
    try:
        _create_user()
        monkeypatch.setattr(account_router, "_generate_code", lambda: "123456")
        monkeypatch.setattr(account_router, "send_code", lambda *args, **kwargs: True)

        token = csrf_token(client.get("/login/code").text)
        response = client.post(
            "/login/code/send",
            data={"csrf_token": token, "email": EMAIL},
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert response.headers["location"] == "/login/code"

        token = csrf_token(client.get("/login/code").text)
        response = client.post(
            "/login/code/verify",
            data={"csrf_token": token, "code": "123456"},
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert NICKNAME in client.get("/").text
    finally:
        _cleanup_user()


def test_code_login_unregistered(client, monkeypatch):
    _cleanup_user()
    monkeypatch.setattr(account_router, "_generate_code", lambda: "123456")
    monkeypatch.setattr(account_router, "send_code", lambda *args, **kwargs: True)

    token = csrf_token(client.get("/login/code").text)
    response = client.post(
        "/login/code/send",
        data={"csrf_token": token, "email": EMAIL},
        follow_redirects=False,
    )
    assert response.status_code == 400
    assert "尚未注册" in response.text


def test_code_login_wrong_code(client, monkeypatch):
    _cleanup_user()
    try:
        _create_user()
        monkeypatch.setattr(account_router, "_generate_code", lambda: "123456")
        monkeypatch.setattr(account_router, "send_code", lambda *args, **kwargs: True)

        token = csrf_token(client.get("/login/code").text)
        client.post(
            "/login/code/send",
            data={"csrf_token": token, "email": EMAIL},
            follow_redirects=False,
        )

        token = csrf_token(client.get("/login/code").text)
        response = client.post(
            "/login/code/verify",
            data={"csrf_token": token, "code": "000000"},
            follow_redirects=False,
        )
        assert response.status_code == 400
        assert "验证码错误" in response.text
        assert NICKNAME not in client.get("/").text
    finally:
        _cleanup_user()


def test_login_safe_next(client):
    _cleanup_user()
    try:
        _create_user()

        token = csrf_token(client.get("/login?next=//evil.com").text)
        response = client.post(
            "/login",
            data={
                "csrf_token": token,
                "email": EMAIL,
                "password": PASSWORD,
                "next": "//evil.com",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert response.headers["location"] == "/"
    finally:
        _cleanup_user()


def test_password_reset(client, monkeypatch):
    _cleanup_user()
    try:
        _create_user()
        monkeypatch.setattr(account_router, "_generate_code", lambda: "123456")
        monkeypatch.setattr(account_router, "send_code", lambda *args, **kwargs: True)

        token = csrf_token(client.get("/forgot-password").text)
        response = client.post(
            "/forgot-password",
            data={"csrf_token": token, "email": EMAIL},
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert response.headers["location"] == "/reset-password"

        token = csrf_token(client.get("/reset-password").text)
        response = client.post(
            "/reset-password",
            data={
                "csrf_token": token,
                "code": "123456",
                "password": NEW_PASSWORD,
                "confirm": NEW_PASSWORD,
            },
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert response.headers["location"] == "/login?reset=1"

        with SessionLocal() as db:
            user = db.scalar(select(User).where(User.email == EMAIL))
            assert user is not None
            assert PasswordHash.recommended().verify(NEW_PASSWORD, user.password_hash)
            assert (
                db.scalar(
                    select(VerificationCode.id).where(VerificationCode.email == EMAIL)
                )
                is None
            )

        token = csrf_token(client.get("/login").text)
        response = client.post(
            "/login",
            data={
                "csrf_token": token,
                "email": EMAIL,
                "password": NEW_PASSWORD,
            },
            follow_redirects=False,
        )
        assert response.status_code == 303
    finally:
        _cleanup_user()


def test_public_login_rate_limit(client):
    token = csrf_token(client.get("/login").text)
    for _ in range(5):
        response = client.post(
            "/login",
            data={
                "csrf_token": token,
                "email": "nobody@example.com",
                "password": "wrong",
            },
            follow_redirects=False,
        )
        assert response.status_code == 400

    response = client.post(
        "/login",
        data={
            "csrf_token": token,
            "email": "nobody@example.com",
            "password": "wrong",
        },
        follow_redirects=False,
    )
    assert response.status_code == 429
    assert response.headers["retry-after"] == "300"


def _session_data(client) -> dict:
    cookie = client.cookies.get("blog_session")
    assert cookie is not None
    payload = cookie.split(".", 1)[0]
    payload += "=" * (-len(payload) % 4)
    return json.loads(base64.urlsafe_b64decode(payload))


def test_reset_code_is_not_stored_in_session_cookie(client, monkeypatch):
    _cleanup_user()
    try:
        _create_user()
        monkeypatch.setattr(account_router, "_generate_code", lambda: "123456")
        monkeypatch.setattr(account_router, "send_code", lambda *args, **kwargs: True)

        token = csrf_token(client.get("/forgot-password").text)
        response = client.post(
            "/forgot-password",
            data={"csrf_token": token, "email": EMAIL},
            follow_redirects=False,
        )
        assert response.status_code == 303

        session = _session_data(client)
        pending = session["pending_reset"]
        assert pending.get("code_id") is not None
        assert "code" not in pending
        assert "123456" not in json.dumps(session, ensure_ascii=False)

        token = csrf_token(client.get("/reset-password").text)
        response = client.post(
            "/reset-password",
            data={
                "csrf_token": token,
                "code": "123456",
                "password": NEW_PASSWORD,
                "confirm": NEW_PASSWORD,
            },
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert response.headers["location"] == "/login?reset=1"
    finally:
        _cleanup_user()


def test_register_code_and_password_hash_not_in_session_cookie(client, monkeypatch):
    _cleanup_user()
    try:
        monkeypatch.setattr(account_router, "_generate_code", lambda: "654321")
        monkeypatch.setattr(account_router, "send_code", lambda *args, **kwargs: True)

        token = csrf_token(client.get("/register").text)
        response = client.post(
            "/register",
            data={
                "csrf_token": token,
                "email": EMAIL,
                "nickname": NICKNAME,
                "password": PASSWORD,
                "confirm": PASSWORD,
            },
            follow_redirects=False,
        )
        assert response.status_code == 303

        session = _session_data(client)
        pending = session["pending_registration"]
        assert pending.get("code_id") is not None
        assert "code" not in pending
        assert "password_hash" not in pending
        assert "654321" not in json.dumps(session, ensure_ascii=False)

        token = csrf_token(client.get("/register/verify").text)
        response = client.post(
            "/register/verify",
            data={"csrf_token": token, "code": "654321"},
            follow_redirects=False,
        )
        assert response.status_code == 303
        with SessionLocal() as db:
            assert db.scalar(select(User).where(User.email == EMAIL)) is not None
    finally:
        _cleanup_user()


def test_login_code_is_not_stored_in_session_cookie(client, monkeypatch):
    _cleanup_user()
    try:
        _create_user()
        monkeypatch.setattr(account_router, "_generate_code", lambda: "112233")
        monkeypatch.setattr(account_router, "send_code", lambda *args, **kwargs: True)

        token = csrf_token(client.get("/login/code").text)
        response = client.post(
            "/login/code/send",
            data={"csrf_token": token, "email": EMAIL},
            follow_redirects=False,
        )
        assert response.status_code == 303

        session = _session_data(client)
        pending = session["pending_login_code"]
        assert pending.get("code_id") is not None
        assert "code" not in pending
        assert "112233" not in json.dumps(session, ensure_ascii=False)

        token = csrf_token(client.get("/login/code").text)
        response = client.post(
            "/login/code/verify",
            data={"csrf_token": token, "code": "112233"},
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert NICKNAME in client.get("/").text
    finally:
        _cleanup_user()


DELETED_USER_EMAIL = "__pytest_deleted@example.com"
DELETED_USER_NICKNAME = "__pytest_deleted__"
DELETED_USER_PASSWORD = "DeletedPass123!"


def _cleanup_deleted_user() -> None:
    with SessionLocal() as db:
        db.execute(delete(User).where(User.email == DELETED_USER_EMAIL))
        db.execute(delete(User).where(User.username == DELETED_USER_NICKNAME))
        db.commit()


def _create_deleted_user() -> None:
    with SessionLocal() as db:
        db.add(
            User(
                email=DELETED_USER_EMAIL,
                username=DELETED_USER_NICKNAME,
                password_hash=PasswordHash.recommended().hash(DELETED_USER_PASSWORD),
            )
        )
        db.commit()


def _login_deleted_user(client) -> None:
    token = csrf_token(client.get("/login").text)
    response = client.post(
        "/login",
        data={
            "csrf_token": token,
            "email": DELETED_USER_EMAIL,
            "password": DELETED_USER_PASSWORD,
        },
        follow_redirects=False,
    )
    assert response.status_code == 303


def test_self_delete_blocks_email_for_24_hours(monkeypatch):
    _cleanup_deleted_user()
    monkeypatch.setattr(account_router, "_generate_code", lambda: "778899")
    monkeypatch.setattr(account_router, "send_code", lambda *args, **kwargs: True)
    try:
        _create_deleted_user()
        with TestClient(app) as client:
            _login_deleted_user(client)

            page = client.get("/account/delete")
            assert page.status_code == 200
            token = csrf_token(page.text)
            response = client.post(
                "/account/delete",
                data={
                    "csrf_token": token,
                    "password": DELETED_USER_PASSWORD,
                },
                follow_redirects=False,
            )
            assert response.status_code == 303
            assert response.headers["location"] == "/login?deleted=1"

        with SessionLocal() as db:
            assert (
                db.scalar(select(User).where(User.email == DELETED_USER_EMAIL)) is None
            )

        with TestClient(app) as fresh:
            token = csrf_token(fresh.get("/register").text)
            response = fresh.post(
                "/register",
                data={
                    "csrf_token": token,
                    "email": DELETED_USER_EMAIL,
                    "nickname": "__pytest_deleted_again__",
                    "password": DELETED_USER_PASSWORD,
                    "confirm": DELETED_USER_PASSWORD,
                },
                follow_redirects=False,
            )
            assert response.status_code == 400
            assert "24" in response.text or "注销" in response.text

        with SessionLocal() as db:
            block = db.scalar(
                select(EmailRegistrationBlock).where(
                    EmailRegistrationBlock.email == DELETED_USER_EMAIL
                )
            )
            assert block is not None
            block.blocked_until = datetime.now(UTC).replace(tzinfo=None) - timedelta(
                seconds=1
            )
            db.commit()

        with TestClient(app) as fresh:
            token = csrf_token(fresh.get("/register").text)
            response = fresh.post(
                "/register",
                data={
                    "csrf_token": token,
                    "email": DELETED_USER_EMAIL,
                    "nickname": "__pytest_deleted_again__",
                    "password": DELETED_USER_PASSWORD,
                    "confirm": DELETED_USER_PASSWORD,
                },
                follow_redirects=False,
            )
            assert response.status_code == 303

            token = csrf_token(fresh.get("/register/verify").text)
            response = fresh.post(
                "/register/verify",
                data={"csrf_token": token, "code": "778899"},
                follow_redirects=False,
            )
            assert response.status_code == 303

        with SessionLocal() as db:
            assert (
                db.scalar(select(User).where(User.email == DELETED_USER_EMAIL))
                is not None
            )
    finally:
        _cleanup_deleted_user()


def test_deleted_user_session_is_cleared(monkeypatch):
    _cleanup_deleted_user()
    try:
        _create_deleted_user()
        with TestClient(app) as client:
            _login_deleted_user(client)
            with SessionLocal() as db:
                db.execute(delete(User).where(User.email == DELETED_USER_EMAIL))
                db.commit()

            response = client.get("/")
            assert response.status_code == 200
            assert DELETED_USER_NICKNAME not in response.text
            assert client.get("/login", follow_redirects=False).status_code == 200
    finally:
        _cleanup_deleted_user()


def test_password_reset_invalidates_existing_sessions(monkeypatch):
    _cleanup_deleted_user()
    monkeypatch.setattr(account_router, "_generate_code", lambda: "445566")
    monkeypatch.setattr(account_router, "send_code", lambda *args, **kwargs: True)
    try:
        _create_deleted_user()
        with TestClient(app) as client:
            _login_deleted_user(client)

            token = csrf_token(client.get("/forgot-password").text)
            response = client.post(
                "/forgot-password",
                data={"csrf_token": token, "email": DELETED_USER_EMAIL},
                follow_redirects=False,
            )
            assert response.status_code == 303

            token = csrf_token(client.get("/reset-password").text)
            response = client.post(
                "/reset-password",
                data={
                    "csrf_token": token,
                    "code": "445566",
                    "password": "ResetPass123!",
                    "confirm": "ResetPass123!",
                },
                follow_redirects=False,
            )
            assert response.status_code == 303

            response = client.get("/")
            assert response.status_code == 200
            assert DELETED_USER_NICKNAME not in response.text
            assert client.get("/login", follow_redirects=False).status_code == 200
    finally:
        _cleanup_deleted_user()
