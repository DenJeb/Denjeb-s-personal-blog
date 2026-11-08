"""
========== 评论 / 动态评论 / 留言的写入服务 ==========

把 HTML 路由和 JSON API 共用的“校验 + 限流 + 审核入库”逻辑放在这里。
"""

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models import BlogPost, Moment, User
from app.rate_limit import is_rate_limited, record_event
from app.services.comments import add_comment, add_message, add_moment_comment

INTERACTION_COOLDOWN_SECONDS = 15


@dataclass(frozen=True)
class InteractionResult:
    ok: bool
    code: str
    message: str


def create_comment(
    db: Session,
    post: BlogPost,
    author: str,
    actor_key: str,
    user_id: int | None,
    content: str,
) -> InteractionResult:
    body = content.strip()
    if not body:
        return InteractionResult(False, "invalid", "评论内容不能为空。")

    bucket = f"comment:{actor_key}"
    if is_rate_limited(db, bucket, INTERACTION_COOLDOWN_SECONDS, 1):
        return InteractionResult(False, "too_fast", "评论太快了，请 15 秒后再试。")

    record_event(db, bucket)
    add_comment(db, post, author, user_id, body)
    db.commit()
    return InteractionResult(True, "submitted", "评论已提交，审核通过后会显示。")


def create_moment_comment(
    db: Session,
    moment: Moment,
    author: str,
    actor_key: str,
    user_id: int | None,
    content: str,
) -> InteractionResult:
    body = content.strip()
    if not body:
        return InteractionResult(False, "invalid", "评论内容不能为空。")

    bucket = f"moment_comment:{actor_key}"
    if is_rate_limited(db, bucket, INTERACTION_COOLDOWN_SECONDS, 1):
        return InteractionResult(False, "too_fast", "评论太快了，请 15 秒后再试。")

    record_event(db, bucket)
    add_moment_comment(db, moment, author, user_id, body)
    db.commit()
    return InteractionResult(True, "submitted", "评论已提交，审核通过后会显示。")


def create_message(
    db: Session,
    user: User,
    content: str,
) -> InteractionResult:
    body = content.strip()
    if not body:
        return InteractionResult(False, "invalid", "留言内容不能为空。")

    bucket = f"message:{user.id}"
    if is_rate_limited(db, bucket, INTERACTION_COOLDOWN_SECONDS, 1):
        return InteractionResult(False, "too_fast", "留言太快了，请 15 秒后再试。")

    record_event(db, bucket)
    add_message(db, user, body)
    db.commit()
    return InteractionResult(True, "submitted", "留言已提交。")
