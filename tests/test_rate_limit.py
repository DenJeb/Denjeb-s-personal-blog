"""
========== 限流时间戳测试 ==========
"""

from datetime import UTC, datetime

from app.models import RateLimitEvent
from app.rate_limit import record_event


class _FakeSession:
    def __init__(self):
        self.added = []

    def execute(self, *args, **kwargs):
        return None

    def add(self, obj):
        self.added.append(obj)

    def commit(self):
        pass


def test_record_event_sets_utc_timestamp():
    db = _FakeSession()
    record_event(db, "pytest_bucket")

    assert len(db.added) == 1
    event = db.added[0]
    assert isinstance(event, RateLimitEvent)
    assert event.created_at is not None

    utc_now = datetime.now(UTC).replace(tzinfo=None)
    assert abs((event.created_at - utc_now).total_seconds()) < 5
