"""
========== 评论 / 留言服务：创建内容并写入管理员通知 ==========
"""

from sqlalchemy.orm import Session

from app.models import BlogPost, Comment, Message, Moment, MomentComment, User
from app.services.notifications import (
    notify_new_comment,
    notify_new_message,
    notify_new_moment_comment,
)


def add_comment(
    db: Session,
    post: BlogPost,
    author: str,
    user_id: int | None,
    content: str,
) -> Comment:
    comment = Comment(
        post_id=post.id,
        user_id=user_id,
        author_name=author,
        content=content,
    )
    db.add(comment)
    notify_new_comment(db, comment, post.title)
    return comment


def add_moment_comment(
    db: Session,
    moment: Moment,
    author: str,
    user_id: int | None,
    content: str,
) -> MomentComment:
    comment = MomentComment(
        moment_id=moment.id,
        user_id=user_id,
        author_name=author,
        content=content,
    )
    db.add(comment)
    notify_new_moment_comment(db, comment, moment.content)
    return comment


def add_message(db: Session, user: User, content: str) -> Message:
    message = Message(user_id=user.id, author_name=user.username, content=content)
    db.add(message)
    notify_new_message(db, message)
    return message
