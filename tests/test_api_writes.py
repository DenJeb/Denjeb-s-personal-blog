from sqlalchemy import delete, select

from app.db import SessionLocal
from app.models import Comment, Message, Moment, MomentComment
from tests.conftest import USER_NICKNAME

COMMENT_BODY = "__pytest_api_comment__"
MOMENT_BODY = "__pytest_api_moment_comment__"
MESSAGE_BODY = "__pytest_api_message__"


def _csrf(client) -> str:
    response = client.get("/api/v1/auth/csrf")
    assert response.status_code == 200
    return response.json()["csrf_token"]


def _headers(client) -> dict[str, str]:
    return {"X-CSRF-Token": _csrf(client)}


def _cleanup() -> None:
    with SessionLocal() as db:
        db.execute(delete(Comment).where(Comment.content == COMMENT_BODY))
        db.execute(delete(MomentComment).where(MomentComment.content == MOMENT_BODY))
        db.execute(delete(Message).where(Message.content == MESSAGE_BODY))
        db.commit()


def test_comment_requires_login(client):
    response = client.post(
        "/api/v1/posts/1/comments",
        headers=_headers(client),
        json={"content": COMMENT_BODY},
    )
    assert response.status_code == 401


def test_comment_requires_csrf(user_client):
    response = user_client.post(
        "/api/v1/posts/1/comments",
        json={"content": COMMENT_BODY},
    )
    assert response.status_code == 400


def test_comment_created_unapproved(user_client):
    _cleanup()
    try:
        response = user_client.post(
            "/api/v1/posts/1/comments",
            headers=_headers(user_client),
            json={"content": COMMENT_BODY},
        )
        assert response.status_code == 201
        assert response.json()["ok"] is True

        with SessionLocal() as db:
            comment = db.scalar(select(Comment).where(Comment.content == COMMENT_BODY))
            assert comment is not None
            assert comment.author_name == USER_NICKNAME
            assert comment.is_approved is False
    finally:
        _cleanup()


def test_comment_rejects_empty_content(user_client):
    response = user_client.post(
        "/api/v1/posts/1/comments",
        headers=_headers(user_client),
        json={"content": "   "},
    )
    assert response.status_code == 400
    assert "不能为空" in response.json()["detail"]


def test_comment_honeypot_is_silently_accepted(user_client):
    _cleanup()
    try:
        response = user_client.post(
            "/api/v1/posts/1/comments",
            headers=_headers(user_client),
            json={"content": COMMENT_BODY, "website": "spam"},
        )
        assert response.status_code == 201
        with SessionLocal() as db:
            assert (
                db.scalar(select(Comment).where(Comment.content == COMMENT_BODY))
                is None
            )
    finally:
        _cleanup()


def test_comment_rate_limit(user_client):
    _cleanup()
    try:
        headers = _headers(user_client)
        first = user_client.post(
            "/api/v1/posts/1/comments",
            headers=headers,
            json={"content": COMMENT_BODY},
        )
        assert first.status_code == 201

        second = user_client.post(
            "/api/v1/posts/1/comments",
            headers=headers,
            json={"content": COMMENT_BODY + "_second"},
        )
        assert second.status_code == 429
    finally:
        with SessionLocal() as db:
            db.execute(
                delete(Comment).where(
                    Comment.content.in_([COMMENT_BODY, COMMENT_BODY + "_second"])
                )
            )
            db.commit()


def test_moment_comment_created_unapproved(user_client):
    _cleanup()
    with SessionLocal() as db:
        moment = Moment(content=MOMENT_BODY)
        db.add(moment)
        db.commit()
        db.refresh(moment)
        moment_id = moment.id

    try:
        response = user_client.post(
            f"/api/v1/moments/{moment_id}/comments",
            headers=_headers(user_client),
            json={"content": MOMENT_BODY},
        )
        assert response.status_code == 201

        with SessionLocal() as db:
            comment = db.scalar(
                select(MomentComment).where(MomentComment.content == MOMENT_BODY)
            )
            assert comment is not None
            assert comment.author_name == USER_NICKNAME
            assert comment.is_approved is False
    finally:
        _cleanup()
        with SessionLocal() as db:
            moment = db.get(Moment, moment_id)
            if moment is not None:
                db.delete(moment)
                db.commit()


def test_guestbook_created(user_client):
    _cleanup()
    try:
        response = user_client.post(
            "/api/v1/guestbook",
            headers=_headers(user_client),
            json={"content": MESSAGE_BODY},
        )
        assert response.status_code == 201
        with SessionLocal() as db:
            message = db.scalar(select(Message).where(Message.content == MESSAGE_BODY))
            assert message is not None
            assert message.author_name == USER_NICKNAME
    finally:
        _cleanup()


def test_guestbook_requires_login(client):
    response = client.post(
        "/api/v1/guestbook",
        headers=_headers(client),
        json={"content": MESSAGE_BODY},
    )
    assert response.status_code == 401
