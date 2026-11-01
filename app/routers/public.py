"""
========== 公开页面路由 ==========
"""

import json
from datetime import UTC, date, datetime, time
from email.utils import format_datetime
from html import escape as html_escape
from urllib.parse import quote
from xml.etree.ElementTree import Element, SubElement, register_namespace, tostring

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.config import settings
from app.constants import MESSAGES_PER_PAGE, MOMENT_COMMENTS_SHOWN, MOMENTS_PER_PAGE
from app.csrf import verify_csrf
from app.deps import DbSession
from app.models import (
    AdminUser,
    BlogPost,
    Comment,
    Message,
    Moment,
    MomentComment,
    User,
)
from app.rate_limit import is_rate_limited, record_event
from app.templating import templates

router = APIRouter()

POSTS_PER_PAGE = 5
COMMENTS_PER_PAGE = 10
COMMENT_COOLDOWN_SECONDS = 15
AUTHOR_NAME = "DenJeb"
CONTENT_NS = "http://purl.org/rss/1.0/modules/content/"
ATOM_NS = "http://www.w3.org/2005/Atom"

register_namespace("content", CONTENT_NS)
register_namespace("atom", ATOM_NS)


def _visible_post_conditions() -> tuple:
    return (
        BlogPost.is_published.is_(True),
        BlogPost.published_at <= date.today(),
    )


def _is_post_public(post: BlogPost) -> bool:
    return post.is_published and post.published_at <= date.today()


def _current_admin(request: Request, db: Session) -> AdminUser | None:
    admin_id = request.session.get("admin_user_id")
    if admin_id is None:
        return None

    admin = db.get(AdminUser, admin_id)
    if (
        admin is None
        or (admin.email or "").lower() != settings.admin_email_normalized
        or request.session.get("admin_version") != admin.session_version
    ):
        request.session.pop("admin_user_id", None)
        request.session.pop("admin_version", None)
        return None
    return admin


def _admin_logged_in(request: Request, db: Session) -> bool:
    return _current_admin(request, db) is not None


def _post_json_ld(request: Request, post: BlogPost) -> str:
    url = str(request.url_for("post_detail", post_id=post.id))
    data = {
        "@context": "https://schema.org",
        "@type": "BlogPosting",
        "headline": post.title,
        "description": post.summary or post.title,
        "datePublished": post.published_at.isoformat(),
        "dateModified": post.published_at.isoformat(),
        "inLanguage": "zh-CN",
        "author": {"@type": "Person", "name": AUTHOR_NAME},
        "publisher": {"@type": "Person", "name": AUTHOR_NAME},
        "mainEntityOfPage": {"@type": "WebPage", "@id": url},
        "url": url,
        "keywords": post.tags or [],
    }
    return json.dumps(data, ensure_ascii=False).replace("<", "\\u003c")


def _commenter(
    request: Request, db: Session
) -> tuple[str | None, str | None, int | None]:
    user_id = request.session.get("user_id")
    if user_id is not None:
        user = db.get(User, user_id)
        if user is not None and user.is_active:
            return user.username, f"user:{user.id}", user.id
        request.session.pop("user_id", None)
        request.session.pop("user_name", None)

    admin_user = _current_admin(request, db)
    if admin_user is not None:
        return admin_user.username, f"admin:{admin_user.id}", None
    return None, None, None


@router.get("/")
def index(request: Request, page: int | None = Query(None, ge=1)) -> Response:
    if page is not None:
        target = request.url_for("posts_page")
        return RedirectResponse(f"{target}?page={page}", status_code=303)
    return templates.TemplateResponse(
        request=request,
        name="welcome.html",
        context={"app_name": settings.app_name},
    )


@router.get("/posts")
def posts_page(request: Request, db: DbSession, page: int = Query(1, ge=1)) -> Response:
    visible = _visible_post_conditions()
    total = db.scalar(select(func.count()).select_from(BlogPost).where(*visible)) or 0
    total_pages = max((total + POSTS_PER_PAGE - 1) // POSTS_PER_PAGE, 1)
    if page > total_pages:
        target = request.url_for("posts_page")
        return RedirectResponse(f"{target}?page={total_pages}", status_code=303)

    posts = db.scalars(
        select(BlogPost)
        .where(*visible)
        .order_by(BlogPost.published_at.desc(), BlogPost.id.desc())
        .offset((page - 1) * POSTS_PER_PAGE)
        .limit(POSTS_PER_PAGE)
    ).all()
    _attach_sorted_tags(posts)
    return templates.TemplateResponse(
        request=request,
        name="posts.html",
        context={
            "app_name": settings.app_name,
            "posts": posts,
            "total": total,
            "page": page,
            "total_pages": total_pages,
            "has_prev": page > 1,
            "has_next": page < total_pages,
        },
    )


@router.get("/posts/{post_id}")
def post_detail(
    request: Request,
    post_id: int,
    db: DbSession,
    comment_page: int = Query(1, ge=1),
) -> Response:
    post = db.get(BlogPost, post_id)
    if post is None or (
        not _is_post_public(post) and not _admin_logged_in(request, db)
    ):
        raise HTTPException(status_code=404, detail="文章不存在！")

    _attach_sorted_tags([post])
    condition = (Comment.post_id == post_id, Comment.is_approved.is_(True))
    comment_total = (
        db.scalar(select(func.count()).select_from(Comment).where(*condition)) or 0
    )
    comment_total_pages = max(
        (comment_total + COMMENTS_PER_PAGE - 1) // COMMENTS_PER_PAGE, 1
    )
    comment_page = min(max(comment_page, 1), comment_total_pages)
    comments = db.scalars(
        select(Comment)
        .where(*condition)
        .order_by(Comment.created_at.asc())
        .offset((comment_page - 1) * COMMENTS_PER_PAGE)
        .limit(COMMENTS_PER_PAGE)
    ).all()
    commenter, _, _ = _commenter(request, db)
    return templates.TemplateResponse(
        request=request,
        name="post_detail.html",
        context={
            "app_name": settings.app_name,
            "post": post,
            "post_json_ld": _post_json_ld(request, post),
            "comments": comments,
            "comment_total": comment_total,
            "comment_page": comment_page,
            "comment_total_pages": comment_total_pages,
            "comment_has_prev": comment_page > 1,
            "comment_has_next": comment_page < comment_total_pages,
            "commenter": commenter,
        },
    )


@router.post("/posts/{post_id}/comments")
def submit_comment(
    request: Request,
    db: DbSession,
    post_id: int,
    content: str = Form(..., max_length=2000),
    website: str = Form(""),
    _csrf: None = Depends(verify_csrf),
) -> RedirectResponse:
    post = db.get(BlogPost, post_id)
    if post is None or (
        not _is_post_public(post) and not _admin_logged_in(request, db)
    ):
        raise HTTPException(status_code=404, detail="文章不存在！")

    author, actor_key, user_id = _commenter(request, db)
    if author is None or actor_key is None:
        return RedirectResponse(f"/login?next=/posts/{post_id}", status_code=303)

    if website.strip():
        return RedirectResponse(
            f"/posts/{post_id}?comment=submitted#comments", status_code=303
        )

    body = content.strip()
    if not body:
        return RedirectResponse(
            f"/posts/{post_id}?comment=invalid#comments", status_code=303
        )

    bucket = f"comment:{actor_key}"
    if is_rate_limited(db, bucket, COMMENT_COOLDOWN_SECONDS, 1):
        return RedirectResponse(
            f"/posts/{post_id}?comment=too_fast#comments", status_code=303
        )
    record_event(db, bucket)

    db.add(
        Comment(
            post_id=post_id,
            user_id=user_id,
            author_name=author,
            content=body,
        )
    )
    db.commit()
    return RedirectResponse(
        f"/posts/{post_id}?comment=submitted#comments", status_code=303
    )


@router.get("/moments")
def moments_page(
    request: Request, db: DbSession, page: int = Query(1, ge=1)
) -> Response:
    total = db.scalar(select(func.count()).select_from(Moment)) or 0
    total_pages = max((total + MOMENTS_PER_PAGE - 1) // MOMENTS_PER_PAGE, 1)
    if page > total_pages:
        target = request.url_for("moments_page")
        return RedirectResponse(f"{target}?page={total_pages}", status_code=303)

    moments = db.scalars(
        select(Moment)
        .order_by(Moment.created_at.desc(), Moment.id.desc())
        .offset((page - 1) * MOMENTS_PER_PAGE)
        .limit(MOMENTS_PER_PAGE)
    ).all()

    comments_by_moment: dict[int, list[MomentComment]] = {}
    comment_counts: dict[int, int] = {}
    moment_ids = [moment.id for moment in moments]
    if moment_ids:
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
        approved_comments = db.scalars(
            select(MomentComment)
            .where(
                MomentComment.id.in_(
                    select(ranked.c.id).where(ranked.c.rn <= MOMENT_COMMENTS_SHOWN)
                )
            )
            .order_by(MomentComment.created_at.asc(), MomentComment.id.asc())
        ).all()
        for comment in approved_comments:
            comments_by_moment.setdefault(comment.moment_id, []).append(comment)

        comment_counts = dict(
            db.execute(
                select(MomentComment.moment_id, func.count())
                .where(
                    MomentComment.moment_id.in_(moment_ids),
                    MomentComment.is_approved.is_(True),
                )
                .group_by(MomentComment.moment_id)
            ).all()
        )

    commenter, _, _ = _commenter(request, db)
    return templates.TemplateResponse(
        request=request,
        name="moments.html",
        context={
            "app_name": settings.app_name,
            "moments": moments,
            "comments_by_moment": comments_by_moment,
            "comment_counts": comment_counts,
            "commenter": commenter,
            "total": total,
            "page": page,
            "total_pages": total_pages,
            "has_prev": page > 1,
            "has_next": page < total_pages,
        },
    )


@router.post("/moments/{moment_id}/comments")
def submit_moment_comment(
    request: Request,
    db: DbSession,
    moment_id: int,
    content: str = Form(..., max_length=1000),
    website: str = Form(""),
    page: int = Form(1, ge=1),
    _csrf: None = Depends(verify_csrf),
) -> RedirectResponse:
    moment = db.get(Moment, moment_id)
    if moment is None:
        raise HTTPException(status_code=404, detail="动态不存在！")

    author, actor_key, user_id = _commenter(request, db)
    if author is None or actor_key is None:
        next_url = (
            f"/moments?page={page}#moment-{moment_id}"
            if page > 1
            else f"/moments#moment-{moment_id}"
        )
        return RedirectResponse(
            f"/login?next={quote(next_url, safe='')}", status_code=303
        )

    target = request.url_for("moments_page")
    prefix = f"page={page}&comment=" if page > 1 else "comment="
    if website.strip():
        return RedirectResponse(
            f"{target}?{prefix}submitted#moment-{moment_id}", status_code=303
        )

    body = content.strip()
    if not body:
        return RedirectResponse(
            f"{target}?{prefix}invalid#moment-{moment_id}", status_code=303
        )

    bucket = f"moment_comment:{actor_key}"
    if is_rate_limited(db, bucket, COMMENT_COOLDOWN_SECONDS, 1):
        return RedirectResponse(
            f"{target}?{prefix}too_fast#moment-{moment_id}", status_code=303
        )
    record_event(db, bucket)

    db.add(
        MomentComment(
            moment_id=moment_id,
            user_id=user_id,
            author_name=author,
            content=body,
        )
    )
    db.commit()
    return RedirectResponse(
        f"{target}?{prefix}submitted#moment-{moment_id}", status_code=303
    )


@router.get("/guestbook")
def guestbook_page(
    request: Request, db: DbSession, page: int = Query(1, ge=1)
) -> Response:
    total = db.scalar(select(func.count()).select_from(Message)) or 0
    total_pages = max((total + MESSAGES_PER_PAGE - 1) // MESSAGES_PER_PAGE, 1)
    if page > total_pages:
        target = request.url_for("guestbook_page")
        return RedirectResponse(f"{target}?page={total_pages}", status_code=303)

    messages = db.scalars(
        select(Message)
        .order_by(Message.created_at.desc(), Message.id.desc())
        .offset((page - 1) * MESSAGES_PER_PAGE)
        .limit(MESSAGES_PER_PAGE)
    ).all()
    return templates.TemplateResponse(
        request=request,
        name="guestbook.html",
        context={
            "app_name": settings.app_name,
            "messages": messages,
            "user": getattr(request.state, "user", None),
            "total": total,
            "page": page,
            "total_pages": total_pages,
            "has_prev": page > 1,
            "has_next": page < total_pages,
        },
    )


@router.post("/guestbook")
def submit_message(
    request: Request,
    db: DbSession,
    content: str = Form(..., max_length=1000),
    website: str = Form(""),
    _csrf: None = Depends(verify_csrf),
) -> RedirectResponse:
    user = getattr(request.state, "user", None)
    if user is None:
        return RedirectResponse("/login?next=/guestbook", status_code=303)

    target = request.url_for("guestbook_page")
    if website.strip():
        return RedirectResponse(f"{target}?message=submitted", status_code=303)

    body = content.strip()
    if not body:
        return RedirectResponse(f"{target}?message=invalid", status_code=303)

    bucket = f"message:{user.id}"
    if is_rate_limited(db, bucket, COMMENT_COOLDOWN_SECONDS, 1):
        return RedirectResponse(f"{target}?message=too_fast", status_code=303)
    record_event(db, bucket)

    db.add(Message(user_id=user.id, author_name=user.username, content=body))
    db.commit()
    return RedirectResponse(f"{target}?message=submitted", status_code=303)


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


def _tag_sort_key(item: tuple[str, int]) -> tuple[int, str, str]:
    tag, count = item
    return (-count, _pinyin_initial(tag), tag.casefold())


def _visible_tag_counts(db: Session) -> dict[str, int]:
    counts: dict[str, int] = {}
    for tags in db.scalars(
        select(BlogPost.tags).where(*_visible_post_conditions())
    ).all():
        for tag in set(tags or []):
            counts[tag] = counts.get(tag, 0) + 1
    return counts


def _tag_initial_sort_key(tag: str) -> tuple[str, str]:
    return (_pinyin_initial(tag), tag.casefold())


def _attach_sorted_tags(posts: list[BlogPost]) -> None:
    for post in posts:
        post.sorted_tags = sorted(post.tags or [], key=_tag_initial_sort_key)


@router.get("/tags")
def tags_page(
    request: Request,
    db: DbSession,
    tag: str | None = Query(None),
    page: int = Query(1, ge=1),
) -> Response:
    if tag is None or tag == "":
        counts = _visible_tag_counts(db)
        tags = sorted(counts.items(), key=_tag_sort_key)
        return templates.TemplateResponse(
            request=request,
            name="tags.html",
            context={
                "app_name": settings.app_name,
                "tags": tags,
            },
        )

    condition = func.json_contains(BlogPost.tags, json.dumps(tag, ensure_ascii=False))
    visible = _visible_post_conditions()
    total = (
        db.scalar(select(func.count()).select_from(BlogPost).where(condition, *visible))
        or 0
    )
    total_pages = max((total + POSTS_PER_PAGE - 1) // POSTS_PER_PAGE, 1)
    if page > total_pages:
        target = request.url_for("tags_page")
        return RedirectResponse(
            f"{target}?tag={quote(tag, safe='')}&page={total_pages}",
            status_code=303,
        )

    posts = db.scalars(
        select(BlogPost)
        .where(condition, *visible)
        .order_by(BlogPost.published_at.desc(), BlogPost.id.desc())
        .offset((page - 1) * POSTS_PER_PAGE)
        .limit(POSTS_PER_PAGE)
    ).all()
    _attach_sorted_tags(posts)
    return templates.TemplateResponse(
        request=request,
        name="tag.html",
        context={
            "app_name": settings.app_name,
            "tag": tag,
            "posts": posts,
            "total": total,
            "page": page,
            "total_pages": total_pages,
            "has_prev": page > 1,
            "has_next": page < total_pages,
        },
    )


@router.get("/archive")
def archive_page(request: Request, db: DbSession) -> Response:
    posts = db.scalars(
        select(BlogPost)
        .where(*_visible_post_conditions())
        .order_by(BlogPost.published_at.desc(), BlogPost.id.desc())
    ).all()

    archive: dict[int, dict[int, list[BlogPost]]] = {}
    for post in posts:
        archive.setdefault(post.published_at.year, {}).setdefault(
            post.published_at.month, []
        ).append(post)

    return templates.TemplateResponse(
        request=request,
        name="archive.html",
        context={
            "app_name": settings.app_name,
            "archive": archive,
            "total": len(posts),
        },
    )


@router.get("/search")
def search_page(
    request: Request,
    db: DbSession,
    q: str = Query("", max_length=100),
    page: int = Query(1, ge=1),
) -> Response:
    query = q.strip()
    posts = []
    total = 0
    total_pages = 1
    has_prev = False
    has_next = False

    if query:
        escaped = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        pattern = f"%{escaped}%"
        condition = or_(
            BlogPost.title.like(pattern, escape="\\"),
            BlogPost.summary.like(pattern, escape="\\"),
            BlogPost.content.like(pattern, escape="\\"),
        )
        visible = _visible_post_conditions()
        total = (
            db.scalar(
                select(func.count()).select_from(BlogPost).where(condition, *visible)
            )
            or 0
        )
        total_pages = max((total + POSTS_PER_PAGE - 1) // POSTS_PER_PAGE, 1)
        if page > total_pages:
            target = request.url_for("search_page")
            return RedirectResponse(
                f"{target}?q={quote(query, safe='')}&page={total_pages}",
                status_code=303,
            )

        posts = db.scalars(
            select(BlogPost)
            .where(condition, *visible)
            .order_by(BlogPost.published_at.desc(), BlogPost.id.desc())
            .offset((page - 1) * POSTS_PER_PAGE)
            .limit(POSTS_PER_PAGE)
        ).all()
        _attach_sorted_tags(posts)
        has_prev = page > 1
        has_next = page < total_pages
    else:
        page = 1

    return templates.TemplateResponse(
        request=request,
        name="search.html",
        context={
            "app_name": settings.app_name,
            "q": query,
            "posts": posts,
            "total": total,
            "page": page,
            "total_pages": total_pages,
            "has_prev": has_prev,
            "has_next": has_next,
        },
    )


@router.get("/rss.xml")
def rss_feed(
    request: Request,
    db: DbSession,
    full: bool = Query(False),
) -> Response:
    posts = db.scalars(
        select(BlogPost)
        .where(*_visible_post_conditions())
        .order_by(BlogPost.published_at.desc(), BlogPost.id.desc())
        .limit(20)
    ).all()

    site_url = str(request.base_url).rstrip("/")
    rss = Element("rss", version="2.0")
    channel = SubElement(rss, "channel")
    SubElement(channel, "title").text = settings.app_name
    SubElement(channel, "link").text = site_url
    SubElement(channel, "description").text = f"{settings.app_name} 的最新文章"
    SubElement(channel, "language").text = "zh-CN"
    SubElement(
        channel,
        f"{{{ATOM_NS}}}link",
        rel="self",
        type="application/rss+xml",
        href=f"{site_url}/rss.xml",
    )
    SubElement(channel, "lastBuildDate").text = format_datetime(datetime.now(UTC))

    for post in posts:
        item = SubElement(channel, "item")
        SubElement(item, "title").text = post.title
        link = str(request.url_for("post_detail", post_id=post.id))
        SubElement(item, "link").text = link
        SubElement(item, "guid").text = link
        SubElement(item, "pubDate").text = format_datetime(
            datetime.combine(post.published_at, time.min).replace(tzinfo=UTC)
        )
        SubElement(item, "description").text = post.summary or ""
        if full:
            content_html = post.content_html or f"<p>{html_escape(post.content)}</p>"
            SubElement(item, f"{{{CONTENT_NS}}}encoded").text = content_html
        for tag in post.tags or []:
            SubElement(item, "category").text = tag

    xml = '<?xml version="1.0" encoding="UTF-8"?>\n' + tostring(rss, encoding="unicode")
    return Response(content=xml, media_type="application/rss+xml; charset=utf-8")


@router.get("/sitemap.xml")
def sitemap(request: Request, db: DbSession) -> Response:
    urls: list[tuple[str, str | None]] = [
        (str(request.url_for("index")), None),
        (str(request.url_for("posts_page")), None),
        (str(request.url_for("moments_page")), None),
        (str(request.url_for("guestbook_page")), None),
        (str(request.url_for("tags_page")), None),
        (str(request.url_for("archive_page")), None),
        (str(request.url_for("about_page")), None),
    ]

    posts = db.scalars(
        select(BlogPost)
        .where(*_visible_post_conditions())
        .order_by(BlogPost.published_at.desc(), BlogPost.id.desc())
    ).all()
    for post in posts:
        urls.append(
            (
                str(request.url_for("post_detail", post_id=post.id)),
                post.published_at.isoformat(),
            )
        )

    tags = sorted({tag for post in posts for tag in (post.tags or [])})
    tag_base = str(request.url_for("tags_page"))
    for tag in tags:
        urls.append((f"{tag_base}?tag={quote(tag, safe='')}", None))

    urlset = Element("urlset", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
    for loc, lastmod in urls:
        url = SubElement(urlset, "url")
        SubElement(url, "loc").text = loc
        if lastmod:
            SubElement(url, "lastmod").text = lastmod

    xml = '<?xml version="1.0" encoding="UTF-8"?>\n' + tostring(
        urlset, encoding="unicode"
    )
    return Response(content=xml, media_type="application/xml; charset=utf-8")


@router.get("/robots.txt")
def robots_txt(request: Request) -> Response:
    base = str(request.base_url).rstrip("/")
    content = (
        "User-agent: *\n"
        "Allow: /\n"
        "Disallow: /admin/\n"
        "Disallow: /account/\n"
        "Disallow: /login\n"
        "Disallow: /register\n"
        "Disallow: /forgot-password\n"
        "Disallow: /reset-password\n"
        "Disallow: /search\n"
        f"Sitemap: {base}/sitemap.xml\n"
    )
    return Response(content=content, media_type="text/plain; charset=utf-8")


@router.get("/about")
def about_page(request: Request) -> Response:
    return templates.TemplateResponse(
        request=request,
        name="about.html",
        context={"app_name": settings.app_name},
    )
