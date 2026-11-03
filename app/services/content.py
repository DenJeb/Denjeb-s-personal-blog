"""
========== 文章内容服务：可见性、slug、相邻文章、相关文章 ==========
"""

import json
import re
from datetime import date

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.constants import MOMENT_COMMENTS_SHOWN
from app.models import BlogPost, Comment, Message, Moment, MomentComment
from app.slugs import MAX_SLUG_LENGTH, slugify_text


def visible_post_conditions() -> tuple:
    return (
        BlogPost.is_published.is_(True),
        BlogPost.published_at <= date.today(),
    )


def is_post_public(post: BlogPost) -> bool:
    return post.is_published and post.published_at <= date.today()


def unique_post_slug(
    db: Session,
    title: str,
    *,
    post_id: int | None = None,
    requested: str = "",
) -> str:
    base = slugify_text(requested or title, fallback="post")
    candidate = base
    counter = 2
    while True:
        condition = BlogPost.slug == candidate
        if post_id is not None:
            condition = and_(condition, BlogPost.id != post_id)
        if db.scalar(select(BlogPost.id).where(condition)) is None:
            return candidate
        suffix = f"-{counter}"
        candidate = f"{base[: MAX_SLUG_LENGTH - len(suffix)]}{suffix}"
        counter += 1


def find_post(db: Session, identifier: str) -> BlogPost | None:
    if identifier.isdigit():
        post = db.get(BlogPost, int(identifier))
        if post is not None:
            return post
    return db.scalar(select(BlogPost).where(BlogPost.slug == identifier))


def adjacent_posts(
    db: Session, post: BlogPost
) -> tuple[BlogPost | None, BlogPost | None]:
    visible = visible_post_conditions()
    older = db.scalar(
        select(BlogPost)
        .where(
            *visible,
            or_(
                BlogPost.published_at < post.published_at,
                and_(
                    BlogPost.published_at == post.published_at,
                    BlogPost.id < post.id,
                ),
            ),
        )
        .order_by(BlogPost.published_at.desc(), BlogPost.id.desc())
        .limit(1)
    )
    newer = db.scalar(
        select(BlogPost)
        .where(
            *visible,
            or_(
                BlogPost.published_at > post.published_at,
                and_(
                    BlogPost.published_at == post.published_at,
                    BlogPost.id > post.id,
                ),
            ),
        )
        .order_by(BlogPost.published_at.asc(), BlogPost.id.asc())
        .limit(1)
    )
    return older, newer


def related_posts(db: Session, post: BlogPost, limit: int = 3) -> list[BlogPost]:
    candidates = db.scalars(
        select(BlogPost)
        .where(*visible_post_conditions(), BlogPost.id != post.id)
        .order_by(BlogPost.published_at.desc(), BlogPost.id.desc())
        .limit(50)
    ).all()

    tags = set(post.tags or [])
    scored = []
    for candidate in candidates:
        overlap = len(tags & set(candidate.tags or []))
        if overlap:
            scored.append((overlap, candidate))

    scored.sort(
        key=lambda item: (
            -item[0],
            -item[1].published_at.toordinal(),
            -item[1].id,
        )
    )
    if scored:
        return [candidate for _, candidate in scored[:limit]]
    return candidates[:limit]


def reading_minutes(content: str) -> int:
    cjk = len(re.findall(r"[一-鿿]", content))
    words = len(re.findall(r"[A-Za-z0-9_]+", content))
    minutes = cjk / 400 + words / 200
    return max(1, round(minutes))


# GB2312 常用汉字的拼音首字母区间，用来给中文标签按拼音首字母排序。
# 不在区间内的字符会退回按字符本身排序。
_PINYIN_INITIAL_RANGES = (
    ("A", 0xB0A1, 0xB0C4),
    ("B", 0xB0C5, 0xB2C0),
    ("C", 0xB2C1, 0xB4ED),
    ("D", 0xB4EE, 0xB6E9),
    ("E", 0xB6EA, 0xB7A1),
    ("F", 0xB7A2, 0xB8C0),
    ("G", 0xB8C1, 0xB9FD),
    ("H", 0xB9FE, 0xBBF6),
    ("J", 0xBBF7, 0xBFA5),
    ("K", 0xBFA6, 0xC0AB),
    ("L", 0xC0AC, 0xC2E7),
    ("M", 0xC2E8, 0xC4C2),
    ("N", 0xC4C3, 0xC5B5),
    ("O", 0xC5B6, 0xC5BD),
    ("P", 0xC5BE, 0xC6D9),
    ("Q", 0xC6DA, 0xC8BA),
    ("R", 0xC8BB, 0xC8F5),
    ("S", 0xC8F6, 0xCBF9),
    ("T", 0xCBFA, 0xCDD9),
    ("W", 0xCDDA, 0xCEF3),
    ("X", 0xCEF4, 0xD1B8),
    ("Y", 0xD1B9, 0xD4D0),
    ("Z", 0xD4D1, 0xD7F9),
)


def _pinyin_initial(tag: str) -> str:
    first = tag.strip()[:1]
    if not first or first.isascii():
        return first.casefold()
    try:
        encoded = first.encode("gbk")
    except UnicodeEncodeError:
        return first.casefold()
    if len(encoded) != 2:
        return first.casefold()
    code = (encoded[0] << 8) | encoded[1]
    for initial, start, end in _PINYIN_INITIAL_RANGES:
        if start <= code <= end:
            return initial.casefold()
    return first.casefold()


def tag_sort_key(item: tuple[str, int]) -> tuple[int, str, str]:
    tag, count = item
    return (-count, _pinyin_initial(tag), tag.casefold())


def tag_initial_sort_key(tag: str) -> tuple[str, str]:
    return (_pinyin_initial(tag), tag.casefold())


def attach_sorted_tags(posts: list[BlogPost]) -> None:
    for post in posts:
        post.sorted_tags = sorted(post.tags or [], key=tag_initial_sort_key)


def visible_tag_counts(db: Session) -> dict[str, int]:
    counts: dict[str, int] = {}
    for tags in db.scalars(
        select(BlogPost.tags).where(*visible_post_conditions())
    ).all():
        for tag in set(tags or []):
            counts[tag] = counts.get(tag, 0) + 1
    return counts


def _page_bounds(page: int, per_page: int, total: int) -> tuple[int, int]:
    total_pages = max((total + per_page - 1) // per_page, 1)
    return min(max(page, 1), total_pages), total_pages


def paginate_posts(
    db: Session,
    page: int,
    per_page: int,
    *,
    tag: str | None = None,
    query: str | None = None,
) -> tuple[list[BlogPost], int, int, int]:
    conditions = list(visible_post_conditions())

    if tag:
        conditions.append(
            func.json_contains(BlogPost.tags, json.dumps(tag, ensure_ascii=False))
        )

    if query:
        escaped = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        pattern = f"%{escaped}%"
        conditions.append(
            or_(
                BlogPost.title.like(pattern, escape="\\"),
                BlogPost.summary.like(pattern, escape="\\"),
                BlogPost.content.like(pattern, escape="\\"),
            )
        )

    total = (
        db.scalar(select(func.count()).select_from(BlogPost).where(*conditions)) or 0
    )
    page, total_pages = _page_bounds(page, per_page, total)
    posts = db.scalars(
        select(BlogPost)
        .where(*conditions)
        .order_by(BlogPost.published_at.desc(), BlogPost.id.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    ).all()
    attach_sorted_tags(posts)
    return posts, total, page, total_pages


def paginate_comments(
    db: Session, post: BlogPost, page: int, per_page: int
) -> tuple[list[Comment], int, int, int]:
    condition = (Comment.post_id == post.id, Comment.is_approved.is_(True))
    total = db.scalar(select(func.count()).select_from(Comment).where(*condition)) or 0
    page, total_pages = _page_bounds(page, per_page, total)
    comments = db.scalars(
        select(Comment)
        .where(*condition)
        .order_by(Comment.created_at.asc(), Comment.id.asc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    ).all()
    return comments, total, page, total_pages


def paginate_moments(
    db: Session, page: int, per_page: int
) -> tuple[list[Moment], int, int, int]:
    total = db.scalar(select(func.count()).select_from(Moment)) or 0
    page, total_pages = _page_bounds(page, per_page, total)
    moments = db.scalars(
        select(Moment)
        .order_by(Moment.created_at.desc(), Moment.id.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    ).all()
    return moments, total, page, total_pages


def moment_comments_for(
    db: Session, moment_ids: list[int]
) -> tuple[dict[int, list[MomentComment]], dict[int, int]]:
    if not moment_ids:
        return {}, {}

    ranked = (
        select(
            MomentComment.id.label("id"),
            func.row_number()
            .over(
                partition_by=MomentComment.moment_id,
                order_by=(
                    MomentComment.created_at.desc(),
                    MomentComment.id.desc(),
                ),
            )
            .label("rn"),
        )
        .where(
            MomentComment.moment_id.in_(moment_ids),
            MomentComment.is_approved.is_(True),
        )
        .subquery()
    )
    approved = db.scalars(
        select(MomentComment)
        .where(
            MomentComment.id.in_(
                select(ranked.c.id).where(ranked.c.rn <= MOMENT_COMMENTS_SHOWN)
            )
        )
        .order_by(MomentComment.created_at.asc(), MomentComment.id.asc())
    ).all()

    comments_by_moment: dict[int, list[MomentComment]] = {}
    for comment in approved:
        comments_by_moment.setdefault(comment.moment_id, []).append(comment)

    counts = dict(
        db.execute(
            select(MomentComment.moment_id, func.count())
            .where(
                MomentComment.moment_id.in_(moment_ids),
                MomentComment.is_approved.is_(True),
            )
            .group_by(MomentComment.moment_id)
        ).all()
    )
    return comments_by_moment, counts


def paginate_messages(
    db: Session, page: int, per_page: int
) -> tuple[list[Message], int, int, int]:
    total = db.scalar(select(func.count()).select_from(Message)) or 0
    page, total_pages = _page_bounds(page, per_page, total)
    messages = db.scalars(
        select(Message)
        .order_by(Message.created_at.desc(), Message.id.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    ).all()
    return messages, total, page, total_pages


def archive_tree(db: Session) -> dict[int, dict[int, list[BlogPost]]]:
    posts = db.scalars(
        select(BlogPost)
        .where(*visible_post_conditions())
        .order_by(BlogPost.published_at.desc(), BlogPost.id.desc())
    ).all()

    archive: dict[int, dict[int, list[BlogPost]]] = {}
    for post in posts:
        archive.setdefault(post.published_at.year, {}).setdefault(
            post.published_at.month, []
        ).append(post)
    return archive


def all_visible_posts(db: Session, limit: int | None = None) -> list[BlogPost]:
    statement = (
        select(BlogPost)
        .where(*visible_post_conditions())
        .order_by(BlogPost.published_at.desc(), BlogPost.id.desc())
    )
    if limit is not None:
        statement = statement.limit(limit)
    return list(db.scalars(statement).all())
