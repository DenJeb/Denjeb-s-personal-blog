"""
========== 后台用户管理测试 ==========
"""

from pwdlib import PasswordHash
from sqlalchemy import delete, select

from app.db import SessionLocal
from app.models import User
from tests.utils import csrf_token

EMAIL = "__pytest_managed_user@example.com"
NICKNAME = "__pytest_managed_user__"
PASSWORD = "ManagedPass123!"


def _cleanup() -> None:
    with SessionLocal() as db:
        db.execute(delete(User).where(User.email == EMAIL))
        db.execute(delete(User).where(User.username == NICKNAME))
        db.commit()


def _create_user() -> int:
    with SessionLocal() as db:
        db.add(
            User(
                email=EMAIL,
                username=NICKNAME,
                password_hash=PasswordHash.recommended().hash(PASSWORD),
            )
        )
        db.commit()
        return db.scalar(select(User).where(User.email == EMAIL)).id


def test_admin_user_toggle_and_delete(admin_client, client):
    _cleanup()
    try:
        user_id = _create_user()

        page = admin_client.get("/admin/users")
        assert page.status_code == 200
        assert EMAIL in page.text

        token = csrf_token(page.text)
        response = admin_client.post(
            f"/admin/users/{user_id}/toggle",
            data={"csrf_token": token},
            follow_redirects=False,
        )
        assert response.status_code == 303

        with SessionLocal() as db:
            assert db.get(User, user_id).is_active is False

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
        assert response.status_code == 403
        assert "账号已被禁用" in response.text

        page = admin_client.get("/admin/users")
        token = csrf_token(page.text)
        response = admin_client.post(
            f"/admin/users/{user_id}/toggle",
            data={"csrf_token": token},
            follow_redirects=False,
        )
        assert response.status_code == 303
        with SessionLocal() as db:
            assert db.get(User, user_id).is_active is True

        confirm = admin_client.get(f"/admin/users/{user_id}/delete")
        assert confirm.status_code == 200
        token = csrf_token(confirm.text)
        response = admin_client.post(
            f"/admin/users/{user_id}/delete",
            data={"csrf_token": token},
            follow_redirects=False,
        )
        assert response.status_code == 303
        with SessionLocal() as db:
            assert db.get(User, user_id) is None
    finally:
        _cleanup()
