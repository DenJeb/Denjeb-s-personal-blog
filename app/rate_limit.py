"""
========== 数据库限流 ==========

先用数据库存事件，后续可以只替换这一层的实现换成 Redis。
"""

from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models import RateLimitEvent

RATE_LIMIT_RETENTION_SECONDS = 24 * 3600


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def is_rate_limited(
    db: Session,
    bucket: str,
    window_seconds: int,
    max_events: int,
) -> bool:
    cutoff = _now() - timedelta(seconds=window_seconds)
    db.execute(
        delete(RateLimitEvent).where(
            RateLimitEvent.bucket == bucket,
            RateLimitEvent.created_at < cutoff,
        )
    )
    count = (
        db.scalar(
            select(func.count())
            .select_from(RateLimitEvent)
            .where(
                RateLimitEvent.bucket == bucket,
                RateLimitEvent.created_at >= cutoff,
            )
        )
        or 0
    )
    db.commit()
    return count >= max_events


def record_event(db: Session, bucket: str) -> None:
    db.execute(
        delete(RateLimitEvent).where(
            RateLimitEvent.created_at
            < _now() - timedelta(seconds=RATE_LIMIT_RETENTION_SECONDS)
        )
    )
    db.add(RateLimitEvent(bucket=bucket, created_at=_now()))
    db.commit()


def clear_bucket(db: Session, bucket: str) -> None:
    db.execute(delete(RateLimitEvent).where(RateLimitEvent.bucket == bucket))
    db.commit()
