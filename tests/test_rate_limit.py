"""
========== 限流时间戳测试 ==========
"""

from datetime import UTC, datetime

from sqlalchemy import delete, select

from app.db import SessionLocal
from app.models import RateLimitEvent, User
from app.rate_limit import is_rate_limited, record_event


class _FakeSession:
    def __init__(self):
        self.added = []

    def execute(self, *args, **kwargs):
        return None

    def add(self, obj):
        self.added.append(obj)

    def commit(self):
        pass


def test_is_rate_limited_does_not_commit_pending_changes():
    email = "__pytest_rate_limit_commit@example.com"
    with SessionLocal() as db:
        db.execute(delete(User).where(User.email == email))
        db.commit()
        db.add(
            User(
                email=email,
                username="__pytest_rate_limit__",
                password_hash="x",
            )
        )
        is_rate_limited(db, "pytest_commit_bucket", 60, 5)
        db.rollback()

    with SessionLocal() as db:
        assert db.scalar(select(User).where(User.email == email)) is None
        db.execute(delete(User).where(User.email == email))
        db.commit()


def test_record_event_sets_utc_timestamp():
    db = _FakeSession()
    record_event(db, "pytest_bucket")

    assert len(db.added) == 1
    event = db.added[0]
    assert isinstance(event, RateLimitEvent)
    assert event.created_at is not None

    utc_now = datetime.now(UTC).replace(tzinfo=None)
    assert abs((event.created_at - utc_now).total_seconds()) < 5
