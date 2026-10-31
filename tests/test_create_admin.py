"""
========== 管理员创建与密码重置测试 ==========
"""

from pwdlib import PasswordHash
from sqlalchemy import delete, select

from app.config import settings
from app.create_admin import reset_admin_password
from app.db import SessionLocal
from app.models import AdminUser
from tests.utils import csrf_token

ADMIN_EMAIL = settings.admin_email
USERNAME = "__pytest_reset_admin__"
OLD_PASSWORD = "OldAdminPass123!"
NEW_PASSWORD = "NewAdminPass123!"
OTHER_EMAIL = "__pytest_other_admin@example.com"


def _cleanup() -> None:
    with SessionLocal() as db:
        db.execute(delete(AdminUser).where(AdminUser.email == ADMIN_EMAIL))
        db.execute(delete(AdminUser).where(AdminUser.email == OTHER_EMAIL))
        db.commit()


def test_reset_admin_password():
    _cleanup()
    try:
        with SessionLocal() as db:
            db.add(
                AdminUser(
                    username=USERNAME,
                    email=ADMIN_EMAIL,
                    password_hash=PasswordHash.recommended().hash(OLD_PASSWORD),
                )
            )
            db.commit()

        assert reset_admin_password(NEW_PASSWORD) is True

        with SessionLocal() as db:
            admin = db.scalar(select(AdminUser).where(AdminUser.email == ADMIN_EMAIL))
            assert admin is not None
            assert PasswordHash.recommended().verify(NEW_PASSWORD, admin.password_hash)
            assert admin.session_version == 1

        assert reset_admin_password("short") is False
    finally:
        _cleanup()


def test_admin_password_reset_invalidates_session(admin_client):
    assert reset_admin_password("ResetAdmin123!") is True

    response = admin_client.get("/admin/", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/admin/login"


def test_non_fixed_admin_cannot_login(client):
    _cleanup()
    try:
        with SessionLocal() as db:
            db.add(
                AdminUser(
                    username="__pytest_other_admin__",
                    email=OTHER_EMAIL,
                    password_hash=PasswordHash.recommended().hash(OLD_PASSWORD),
                )
            )
            db.commit()

        token = csrf_token(client.get("/admin/login").text)
        response = client.post(
            "/admin/login",
            data={
                "csrf_token": token,
                "username": OTHER_EMAIL,
                "password": OLD_PASSWORD,
            },
            follow_redirects=False,
        )
        assert response.status_code == 400
    finally:
        _cleanup()
