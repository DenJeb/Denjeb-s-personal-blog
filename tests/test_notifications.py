"""
========== 管理员通知测试 ==========
"""

from sqlalchemy import delete, select

from app.db import SessionLocal
from app.models import Comment, Moment, NotificationOutbox
from app.services.notifications import MAX_ATTEMPTS, send_pending
from tests.conftest import TEST_ADMIN_EMAIL
from tests.utils import csrf_token

AUTHOR = "__pytest_user__"
BODY = "unique pytest notification body"


def _cleanup_comments() -> None:
    with SessionLocal() as db:
        db.execute(delete(Comment).where(Comment.author_name == AUTHOR))
        db.commit()


def _outbox() -> list[NotificationOutbox]:
    with SessionLocal() as db:
        return db.scalars(
            select(NotificationOutbox).order_by(NotificationOutbox.id)
        ).all()


def test_comment_notification_enqueued(user_client, monkeypatch):
    _cleanup_comments()
    monkeypatch.setattr("app.routers.public.send_pending_notifications", lambda: None)
    try:
        page = user_client.get("/posts/1")
        token = csrf_token(page.text)
        response = user_client.post(
            "/posts/1/comments",
            data={"csrf_token": token, "content": BODY},
            follow_redirects=False,
        )
        assert response.status_code == 303

        rows = _outbox()
        assert len(rows) == 1
        assert rows[0].kind == "comment"
        assert rows[0].recipient == TEST_ADMIN_EMAIL
        assert BODY in rows[0].body
        assert rows[0].sent_at is None
    finally:
        _cleanup_comments()


def test_guestbook_notification_enqueued(user_client, monkeypatch):
    monkeypatch.setattr("app.routers.public.send_pending_notifications", lambda: None)
    token = csrf_token(user_client.get("/guestbook").text)
    response = user_client.post(
        "/guestbook",
        data={"csrf_token": token, "content": BODY},
        follow_redirects=False,
    )
    assert response.status_code == 303

    rows = _outbox()
    assert len(rows) == 1
    assert rows[0].kind == "message"
    assert BODY in rows[0].body


def test_moment_comment_notification_enqueued(user_client, monkeypatch):
    monkeypatch.setattr("app.routers.public.send_pending_notifications", lambda: None)
    with SessionLocal() as db:
        moment = Moment(content="__pytest_notification_moment__")
        db.add(moment)
        db.commit()
        moment_id = moment.id

    token = csrf_token(user_client.get("/moments").text)
    response = user_client.post(
        f"/moments/{moment_id}/comments",
        data={"csrf_token": token, "content": BODY, "page": "1"},
        follow_redirects=False,
    )
    assert response.status_code == 303

    rows = _outbox()
    assert len(rows) == 1
    assert rows[0].kind == "moment_comment"
    assert BODY in rows[0].body


def test_send_pending_marks_sent():
    with SessionLocal() as db:
        db.add(
            NotificationOutbox(
                kind="test",
                recipient="admin@example.com",
                subject="subject",
                body="body",
            )
        )
        db.commit()

    sent_messages = []

    def fake_sender(to, subject, body):
        sent_messages.append((to, subject, body))
        return True

    assert send_pending(sender=fake_sender) == 1
    assert len(sent_messages) == 1

    with SessionLocal() as db:
        row = db.scalar(select(NotificationOutbox))
        assert row is not None
        assert row.sent_at is not None
        assert row.attempts == 1
        assert row.last_error is None


def test_send_pending_records_failure():
    with SessionLocal() as db:
        db.add(
            NotificationOutbox(
                kind="test",
                recipient="admin@example.com",
                subject="subject",
                body="body",
            )
        )
        db.commit()

    assert send_pending(sender=lambda *args: False) == 0

    with SessionLocal() as db:
        row = db.scalar(select(NotificationOutbox))
        assert row is not None
        assert row.sent_at is None
        assert row.attempts == 1
        assert row.last_error == "发送失败"


def test_send_pending_stops_after_max_attempts():
    with SessionLocal() as db:
        db.add(
            NotificationOutbox(
                kind="test",
                recipient="admin@example.com",
                subject="subject",
                body="body",
                attempts=MAX_ATTEMPTS,
            )
        )
        db.commit()

    called = []
    assert send_pending(sender=lambda *args: called.append(True) or True) == 0
    assert called == []
