"""
========== 管理员通知：站内 outbox + 后台发送 ==========
"""

import argparse
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.db import SessionLocal
from app.mailer import send_email
from app.models import Comment, Message, MomentComment, NotificationOutbox

MAX_ATTEMPTS = 5
EXCERPT_LENGTH = 200


def _excerpt(text: str) -> str:
    text = text.strip()
    if len(text) <= EXCERPT_LENGTH:
        return text
    return text[:EXCERPT_LENGTH] + "…"


def _admin_url(path: str) -> str:
    return f"{settings.site_url.rstrip('/')}{path}"


def _enqueue(db: Session, kind: str, subject: str, body: str) -> NotificationOutbox:
    row = NotificationOutbox(
        kind=kind,
        recipient=settings.admin_email_normalized,
        subject=subject[:200],
        body=body,
    )
    db.add(row)
    return row


def notify_new_comment(db: Session, comment: Comment, post_title: str) -> None:
    _enqueue(
        db,
        "comment",
        f"[{settings.app_name}] 新评论：{post_title}",
        (
            f"文章：《{post_title}》\n"
            f"作者：{comment.author_name}\n"
            f"内容：{_excerpt(comment.content)}\n\n"
            f"审核：{_admin_url('/admin/comments')}"
        ),
    )


def notify_new_moment_comment(
    db: Session, comment: MomentComment, moment_content: str
) -> None:
    _enqueue(
        db,
        "moment_comment",
        f"[{settings.app_name}] 新动态评论",
        (
            f"动态：{_excerpt(moment_content)}\n"
            f"作者：{comment.author_name}\n"
            f"内容：{_excerpt(comment.content)}\n\n"
            f"审核：{_admin_url('/admin/moment-comments')}"
        ),
    )


def notify_new_message(db: Session, message: Message) -> None:
    _enqueue(
        db,
        "message",
        f"[{settings.app_name}] 新留言",
        (
            f"作者：{message.author_name}\n"
            f"内容：{_excerpt(message.content)}\n\n"
            f"查看：{_admin_url('/admin/messages')}"
        ),
    )


def send_pending(sender=None, limit: int = 20) -> int:
    sender = sender or send_email
    sent = 0
    now = datetime.now(UTC).replace(tzinfo=None)

    with SessionLocal() as db:
        rows = db.scalars(
            select(NotificationOutbox)
            .where(
                NotificationOutbox.sent_at.is_(None),
                NotificationOutbox.attempts < MAX_ATTEMPTS,
            )
            .order_by(NotificationOutbox.created_at.asc(), NotificationOutbox.id.asc())
            .limit(limit)
        ).all()

        for row in rows:
            row.attempts += 1
            try:
                delivered = sender(row.recipient, row.subject, row.body)
            except Exception as exc:  # noqa: BLE001
                delivered = False
                row.last_error = str(exc)[:500]
            if delivered:
                row.sent_at = now
                row.last_error = None
                sent += 1
            elif row.last_error is None:
                row.last_error = "发送失败"

        db.commit()
    return sent


def main() -> None:
    parser = argparse.ArgumentParser(description="发送管理员通知")
    subparsers = parser.add_subparsers(dest="command", required=True)
    send_parser = subparsers.add_parser("send", help="发送 outbox 中待发送的通知")
    send_parser.add_argument("--limit", type=int, default=50)
    args = parser.parse_args()

    if args.command == "send":
        print(f"已发送 {send_pending(limit=args.limit)} 封通知。")


if __name__ == "__main__":
    main()
