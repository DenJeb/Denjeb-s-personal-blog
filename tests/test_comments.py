"""
========== 评论流程测试 ==========
"""

from sqlalchemy import delete, func, select

from app.create_admin import reset_admin_password
from app.db import SessionLocal
from app.models import Comment
from tests.utils import csrf_token

AUTHOR = "__pytest_user__"
BODY = "unique pytest comment body"


def _cleanup_comments() -> None:
    with SessionLocal() as db:
        db.execute(delete(Comment).where(Comment.author_name == AUTHOR))
        db.commit()


def test_comment_flow(user_client, admin_client):
    _cleanup_comments()
    try:
        page = user_client.get("/posts/1")
        token = csrf_token(page.text)
        response = user_client.post(
            "/posts/1/comments",
            data={"csrf_token": token, "content": BODY},
            follow_redirects=False,
        )
        assert response.status_code == 303

        with SessionLocal() as db:
            comment = db.scalar(select(Comment).where(Comment.author_name == AUTHOR))
            assert comment is not None
            assert comment.is_approved is False
            comment_id = comment.id

        public_page = user_client.get("/posts/1")
        assert BODY not in public_page.text

        admin_page = admin_client.get("/admin/comments")
        assert AUTHOR in admin_page.text
        token = csrf_token(admin_page.text)
        response = admin_client.post(
            f"/admin/comments/{comment_id}/approve",
            data={"csrf_token": token},
            follow_redirects=False,
        )
        assert response.status_code == 303

        with SessionLocal() as db:
            assert db.get(Comment, comment_id).is_approved is True

        assert BODY in user_client.get("/posts/1").text

        confirm = admin_client.get(f"/admin/comments/{comment_id}/delete")
        assert confirm.status_code == 200
        token = csrf_token(confirm.text)
        response = admin_client.post(
            f"/admin/comments/{comment_id}/delete",
            data={"csrf_token": token},
            follow_redirects=False,
        )
        assert response.status_code == 303
        with SessionLocal() as db:
            assert db.get(Comment, comment_id) is None
    finally:
        _cleanup_comments()


def test_admin_can_comment(admin_client):
    page = admin_client.get("/posts/1")
    assert "以 __pytest_admin__ 的身份评论" in page.text


def test_comment_requires_login(client):
    _cleanup_comments()
    try:
        post_page = client.get("/posts/1")
        assert "后才能评论" in post_page.text

        token = csrf_token(client.get("/login").text)
        response = client.post(
            "/posts/1/comments",
            data={"csrf_token": token, "content": BODY},
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert response.headers["location"].startswith("/login")

        with SessionLocal() as db:
            assert (
                db.scalar(select(Comment).where(Comment.author_name == AUTHOR)) is None
            )
    finally:
        _cleanup_comments()


def test_comment_honeypot(user_client):
    _cleanup_comments()
    try:
        token = csrf_token(user_client.get("/posts/1").text)
        response = user_client.post(
            "/posts/1/comments",
            data={
                "csrf_token": token,
                "content": BODY,
                "website": "spam",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303
        with SessionLocal() as db:
            assert (
                db.scalar(select(Comment).where(Comment.author_name == AUTHOR)) is None
            )
    finally:
        _cleanup_comments()


def test_comment_rate_limit(user_client):
    _cleanup_comments()
    try:
        token = csrf_token(user_client.get("/posts/1").text)
        response = user_client.post(
            "/posts/1/comments",
            data={"csrf_token": token, "content": BODY},
            follow_redirects=False,
        )
        assert response.status_code == 303

        response = user_client.post(
            "/posts/1/comments",
            data={"csrf_token": token, "content": BODY + " second"},
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert "comment=too_fast" in response.headers["location"]

        with SessionLocal() as db:
            count = db.scalar(
                select(func.count())
                .select_from(Comment)
                .where(Comment.author_name == AUTHOR)
            )
            assert count == 1
    finally:
        _cleanup_comments()


def test_comment_requires_csrf(client):
    response = client.post(
        "/posts/1/comments",
        data={"content": BODY},
        follow_redirects=False,
    )
    assert response.status_code == 422


def test_comment_pagination(client):
    with SessionLocal() as db:
        db.execute(delete(Comment).where(Comment.post_id == 1))
        for index in range(11):
            db.add(
                Comment(
                    post_id=1,
                    author_name=AUTHOR,
                    content=f"{BODY} {index}",
                    is_approved=True,
                )
            )
        db.commit()

    try:
        first = client.get("/posts/1")
        assert "第 1 / 2 页" in first.text

        second = client.get("/posts/1?comment_page=2")
        assert "第 2 / 2 页" in second.text
    finally:
        with SessionLocal() as db:
            db.execute(delete(Comment).where(Comment.post_id == 1))
            db.commit()


def test_stale_admin_session_cannot_comment(admin_client):
    _cleanup_comments()
    try:
        assert reset_admin_password("ResetAdmin123!") is True

        token = csrf_token(admin_client.get("/login").text)
        response = admin_client.post(
            "/posts/1/comments",
            data={"csrf_token": token, "content": BODY},
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert response.headers["location"].startswith("/login")

        with SessionLocal() as db:
            assert (
                db.scalar(select(Comment).where(Comment.author_name == AUTHOR)) is None
            )
    finally:
        _cleanup_comments()
