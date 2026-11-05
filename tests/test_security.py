"""
========== 安全加固测试 ==========
"""

import re

import pyotp
from sqlalchemy import select

from app.config import settings
from app.db import SessionLocal
from app.models import AdminUser
from app.services import accounts as accounts_service
from tests.conftest import ADMIN_EMAIL, ADMIN_PASSWORD
from tests.utils import csrf_token


def _admin() -> AdminUser:
    with SessionLocal() as db:
        admin = db.scalar(select(AdminUser).where(AdminUser.email == ADMIN_EMAIL))
        assert admin is not None
        return admin


def _clear_totp() -> None:
    with SessionLocal() as db:
        admin = db.scalar(select(AdminUser).where(AdminUser.email == ADMIN_EMAIL))
        if admin is not None:
            admin.totp_secret = None
            db.commit()


def test_security_page_requires_admin(client):
    response = client.get("/admin/security", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/admin/login"


def test_enable_totp_and_login(admin_client, client):
    _clear_totp()
    try:
        page = admin_client.get("/admin/security")
        token = csrf_token(page.text)
        response = admin_client.post(
            "/admin/security/totp/start",
            data={"csrf_token": token},
            follow_redirects=False,
        )
        assert response.status_code == 303

        setup = admin_client.get("/admin/security?setup=1")
        match = re.search(r"data-totp-secret>([A-Z2-7]+)<", setup.text)
        assert match is not None
        secret = match.group(1)

        token = csrf_token(setup.text)
        response = admin_client.post(
            "/admin/security/totp/enable",
            data={"csrf_token": token, "code": pyotp.TOTP(secret).now()},
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert _admin().totp_secret == secret

        login_page = client.get("/admin/login")
        token = csrf_token(login_page.text)
        response = client.post(
            "/admin/login",
            data={
                "csrf_token": token,
                "username": ADMIN_EMAIL,
                "password": ADMIN_PASSWORD,
            },
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert response.headers["location"] == "/admin/login/code"

        code_page = client.get("/admin/login/code")
        assert code_page.status_code == 200
        token = csrf_token(code_page.text)
        response = client.post(
            "/admin/login/code",
            data={"csrf_token": token, "code": "123456"},
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert response.headers["location"] == "/admin/login/totp"

        totp_page = client.get("/admin/login/totp")
        assert totp_page.status_code == 200
        token = csrf_token(totp_page.text)
        response = client.post(
            "/admin/login/totp",
            data={"csrf_token": token, "code": pyotp.TOTP(secret).now()},
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert response.headers["location"] == "/admin/"
        assert client.get("/admin/").status_code == 200
    finally:
        _clear_totp()


def test_wrong_totp_code_rejected(admin_client, client):
    _clear_totp()
    try:
        with SessionLocal() as db:
            admin = db.scalar(select(AdminUser).where(AdminUser.email == ADMIN_EMAIL))
            assert admin is not None
            admin.totp_secret = pyotp.random_base32()
            db.commit()

        login_page = client.get("/admin/login")
        token = csrf_token(login_page.text)
        response = client.post(
            "/admin/login",
            data={
                "csrf_token": token,
                "username": ADMIN_EMAIL,
                "password": ADMIN_PASSWORD,
            },
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert response.headers["location"] == "/admin/login/code"

        code_page = client.get("/admin/login/code")
        token = csrf_token(code_page.text)
        response = client.post(
            "/admin/login/code",
            data={"csrf_token": token, "code": "123456"},
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert response.headers["location"] == "/admin/login/totp"

        totp_page = client.get("/admin/login/totp")
        token = csrf_token(totp_page.text)
        response = client.post(
            "/admin/login/totp",
            data={"csrf_token": token, "code": "000000"},
            follow_redirects=False,
        )
        assert response.status_code == 400
        assert "验证码不正确" in response.text
        assert client.get("/admin/", follow_redirects=False).headers["location"] == (
            "/admin/login"
        )
    finally:
        _clear_totp()


def test_admin_login_requires_email_code(admin_client, client):
    login_page = client.get("/admin/login")
    assert "发送验证码" in login_page.text
    token = csrf_token(login_page.text)
    response = client.post(
        "/admin/login",
        data={
            "csrf_token": token,
            "username": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD,
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/admin/login/code"

    # 验证码通过之前，不授予后台会话
    assert client.get("/admin/", follow_redirects=False).headers["location"] == (
        "/admin/login"
    )

    code_page = client.get("/admin/login/code")
    assert code_page.status_code == 200
    token = csrf_token(code_page.text)

    wrong = client.post(
        "/admin/login/code",
        data={"csrf_token": token, "code": "000000"},
        follow_redirects=False,
    )
    assert wrong.status_code == 400
    assert "验证码不正确" in wrong.text

    response = client.post(
        "/admin/login/code",
        data={"csrf_token": token, "code": "123456"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/admin/"
    assert client.get("/admin/").status_code == 200


def test_admin_login_code_resend(admin_client, client, monkeypatch):
    codes = iter(["111111", "222222"])
    monkeypatch.setattr(accounts_service, "generate_code", lambda: next(codes))

    login_page = client.get("/admin/login")
    token = csrf_token(login_page.text)
    response = client.post(
        "/admin/login",
        data={
            "csrf_token": token,
            "username": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD,
        },
        follow_redirects=False,
    )
    assert response.status_code == 303

    code_page = client.get("/admin/login/code")
    token = csrf_token(code_page.text)
    response = client.post(
        "/admin/login/code/resend",
        data={"csrf_token": token},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/admin/login/code?sent=1"

    resent_page = client.get("/admin/login/code?sent=1")
    assert "新的验证码已发送" in resent_page.text

    token = csrf_token(resent_page.text)
    old_code = client.post(
        "/admin/login/code",
        data={"csrf_token": token, "code": "111111"},
        follow_redirects=False,
    )
    assert old_code.status_code == 400

    response = client.post(
        "/admin/login/code",
        data={"csrf_token": token, "code": "222222"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/admin/"


def test_admin_login_code_send_failure(admin_client, client, monkeypatch):
    monkeypatch.setattr(accounts_service, "send_code", lambda *args, **kwargs: False)

    login_page = client.get("/admin/login")
    token = csrf_token(login_page.text)
    response = client.post(
        "/admin/login",
        data={
            "csrf_token": token,
            "username": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD,
        },
        follow_redirects=False,
    )
    assert response.status_code == 503
    assert "验证码发送失败" in response.text
    assert client.get("/admin/", follow_redirects=False).headers["location"] == (
        "/admin/login"
    )


def test_failed_code_sends_count_toward_limit(admin_client, client, monkeypatch):
    monkeypatch.setattr(accounts_service, "send_code", lambda *args, **kwargs: False)

    token = csrf_token(client.get("/admin/login").text)
    for _ in range(5):
        response = client.post(
            "/admin/login",
            data={
                "csrf_token": token,
                "username": ADMIN_EMAIL,
                "password": ADMIN_PASSWORD,
            },
            follow_redirects=False,
        )
        assert response.status_code == 503

    response = client.post(
        "/admin/login",
        data={
            "csrf_token": token,
            "username": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD,
        },
        follow_redirects=False,
    )
    assert response.status_code == 429


def test_admin_login_code_falls_back_to_totp_when_send_fails(
    admin_client, client, monkeypatch
):
    _clear_totp()
    try:
        with SessionLocal() as db:
            admin = db.scalar(select(AdminUser).where(AdminUser.email == ADMIN_EMAIL))
            assert admin is not None
            admin.totp_secret = pyotp.random_base32()
            db.commit()

        monkeypatch.setattr(
            accounts_service, "send_code", lambda *args, **kwargs: False
        )

        login_page = client.get("/admin/login")
        token = csrf_token(login_page.text)
        response = client.post(
            "/admin/login",
            data={
                "csrf_token": token,
                "username": ADMIN_EMAIL,
                "password": ADMIN_PASSWORD,
            },
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert response.headers["location"] == "/admin/login/totp"
    finally:
        _clear_totp()


def test_admin_login_code_cancel(admin_client, client):
    login_page = client.get("/admin/login")
    token = csrf_token(login_page.text)
    response = client.post(
        "/admin/login",
        data={
            "csrf_token": token,
            "username": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD,
        },
        follow_redirects=False,
    )
    assert response.status_code == 303

    code_page = client.get("/admin/login/code")
    token = csrf_token(code_page.text)
    response = client.post(
        "/admin/login/code/cancel",
        data={"csrf_token": token},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/admin/login"
    assert client.get("/admin/login").status_code == 200

    stale = client.post(
        "/admin/login/code",
        data={"csrf_token": token, "code": "123456"},
        follow_redirects=False,
    )
    assert stale.status_code == 303
    assert stale.headers["location"] == "/admin/login"


def test_admin_login_code_resend_revalidates_admin(admin_client, client, monkeypatch):
    sent = []
    monkeypatch.setattr(
        accounts_service,
        "send_code",
        lambda *args, **kwargs: sent.append(True) or True,
    )

    login_page = client.get("/admin/login")
    token = csrf_token(login_page.text)
    response = client.post(
        "/admin/login",
        data={
            "csrf_token": token,
            "username": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD,
        },
        follow_redirects=False,
    )
    assert response.status_code == 303

    with SessionLocal() as db:
        admin = db.scalar(select(AdminUser).where(AdminUser.email == ADMIN_EMAIL))
        assert admin is not None
        admin.session_version += 1
        db.commit()

    sent.clear()
    code_page = client.get("/admin/login/code")
    token = csrf_token(code_page.text)
    response = client.post(
        "/admin/login/code/resend",
        data={"csrf_token": token},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/admin/login"
    assert sent == []


def test_admin_login_code_attempts_exhausted(admin_client, client):
    login_page = client.get("/admin/login")
    token = csrf_token(login_page.text)
    response = client.post(
        "/admin/login",
        data={
            "csrf_token": token,
            "username": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD,
        },
        follow_redirects=False,
    )
    assert response.status_code == 303

    code_page = client.get("/admin/login/code")
    token = csrf_token(code_page.text)
    for index in range(5):
        response = client.post(
            "/admin/login/code",
            data={"csrf_token": token, "code": "000000"},
            follow_redirects=False,
        )
        if index < 4:
            assert response.status_code == 400
        else:
            assert response.status_code == 303
            assert response.headers["location"] == "/admin/login"

    stale = client.post(
        "/admin/login/code",
        data={"csrf_token": token, "code": "123456"},
        follow_redirects=False,
    )
    assert stale.status_code == 303
    assert stale.headers["location"] == "/admin/login"
    assert client.get("/admin/", follow_redirects=False).headers["location"] == (
        "/admin/login"
    )


def test_admin_login_code_can_be_disabled(admin_client, client, monkeypatch):
    monkeypatch.setattr(settings, "admin_login_code_enabled", False)

    login_page = client.get("/admin/login")
    assert "发送验证码" not in login_page.text
    token = csrf_token(login_page.text)
    response = client.post(
        "/admin/login",
        data={
            "csrf_token": token,
            "username": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD,
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/admin/"
    assert client.get("/admin/").status_code == 200


def test_disable_totp(admin_client):
    secret = pyotp.random_base32()
    with SessionLocal() as db:
        admin = db.scalar(select(AdminUser).where(AdminUser.email == ADMIN_EMAIL))
        assert admin is not None
        admin.totp_secret = secret
        db.commit()
        old_version = admin.session_version

    try:
        page = admin_client.get("/admin/security")
        token = csrf_token(page.text)
        response = admin_client.post(
            "/admin/security/totp/disable",
            data={
                "csrf_token": token,
                "password": ADMIN_PASSWORD,
                "code": pyotp.TOTP(secret).now(),
            },
            follow_redirects=False,
        )
        assert response.status_code == 303
        with SessionLocal() as db:
            admin = db.scalar(select(AdminUser).where(AdminUser.email == ADMIN_EMAIL))
            assert admin is not None
            assert admin.totp_secret is None
            assert admin.session_version == old_version + 1
        assert admin_client.get("/admin/security").status_code == 200
    finally:
        _clear_totp()


def test_csp_nonce(client):
    response = client.get("/")
    csp = response.headers["content-security-policy"]
    match = re.search(r"'nonce-([^']+)'", csp)
    assert match is not None
    nonce = match.group(1)
    assert f'nonce="{nonce}"' in response.text
    assert "script-src 'self' 'nonce-" in csp
    assert "script-src 'self' 'unsafe-inline'" not in csp

    post = client.get("/posts/1")
    match = re.search(r"'nonce-([^']+)'", post.headers["content-security-policy"])
    assert match is not None
    assert f'nonce="{match.group(1)}"' in post.text


def test_hsts_when_https_enabled(client, monkeypatch):
    monkeypatch.setattr("app.main.settings.session_https_only", True)
    response = client.get("/")
    assert response.headers["strict-transport-security"] == (
        "max-age=31536000; includeSubDomains"
    )
