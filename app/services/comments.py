"""
========== 评论 / 留言服务：创建内容并写入管理员通知 ==========
"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models import BlogPost, Comment, Message, Moment, MomentComment, User
from app.services.notifications import (
    notify_new_comment,
    notify_new_message,
    notify_new_moment_comment,
)
from app.services.pagination import ADMIN_PAGE_SIZE, page_slice


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


def paginate_admin_comments(
    db: Session, page: int, per_page: int = ADMIN_PAGE_SIZE
) -> tuple[list[Comment], int, int, int]:
    total = db.scalar(select(func.count()).select_from(Comment)) or 0
    page, total_pages = page_slice(page, total, per_page)
    comments = db.scalars(
        select(Comment)
        .options(selectinload(Comment.post))
        .order_by(Comment.created_at.desc(), Comment.id.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    ).all()
    return comments, total, page, total_pages


def toggle_comment(db: Session, comment_id: int) -> Comment | None:
    comment = db.get(Comment, comment_id)
    if comment is None:
        return None
    comment.is_approved = not comment.is_approved
    db.commit()
    return comment


def delete_comment(db: Session, comment_id: int) -> bool:
    comment = db.get(Comment, comment_id)
    if comment is None:
        return False
    db.delete(comment)
    db.commit()
    return True


def paginate_admin_moment_comments(
    db: Session, page: int, per_page: int = ADMIN_PAGE_SIZE
) -> tuple[list[MomentComment], int, int, int]:
    total = db.scalar(select(func.count()).select_from(MomentComment)) or 0
    page, total_pages = page_slice(page, total, per_page)
    comments = db.scalars(
        select(MomentComment)
        .order_by(MomentComment.created_at.desc(), MomentComment.id.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    ).all()
    return comments, total, page, total_pages


def toggle_moment_comment(db: Session, comment_id: int) -> MomentComment | None:
    comment = db.get(MomentComment, comment_id)
    if comment is None:
        return None
    comment.is_approved = not comment.is_approved
    db.commit()
    return comment


def delete_moment_comment(db: Session, comment_id: int) -> bool:
    comment = db.get(MomentComment, comment_id)
    if comment is None:
        return False
    db.delete(comment)
    db.commit()
    return True
