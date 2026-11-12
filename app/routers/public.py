"""
========== 公开页面路由 ==========
"""

import json
from datetime import UTC, datetime, time
from email.utils import format_datetime
from html import escape as html_escape
from urllib.parse import quote
from xml.etree.ElementTree import Element, SubElement, register_namespace, tostring

from fastapi import (
    APIRouter,
    Depends,
    Form,
    HTTPException,
    Query,
    Request,
    Response,
)
from fastapi.responses import RedirectResponse
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.auth import current_admin, current_commenter
from app.config import settings
from app.constants import (
    COMMENTS_PER_PAGE,
    MESSAGES_PER_PAGE,
    MOMENT_COMMENTS_SHOWN,
    MOMENTS_PER_PAGE,
    POSTS_PER_PAGE,
)
from app.csrf import verify_csrf
from app.deps import DbSession
from app.markdown import headings_for
from app.models import (
    BlogPost,
    Comment,
    Message,
    Moment,
    MomentComment,
)
from app.services.content import (
    adjacent_posts,
    attach_sorted_tags,
    find_post,
    is_post_public,
    reading_minutes,
    related_posts,
    tag_sort_key,
    visible_post_conditions,
    visible_tag_counts,
)
from app.services.interactions import (
    create_comment,
    create_message,
    create_moment_comment,
)
from app.templating import templates
from app.time_utils import site_zone

router = APIRouter()

AUTHOR_NAME = settings.author_name
CONTENT_NS = "http://purl.org/rss/1.0/modules/content/"
ATOM_NS = "http://www.w3.org/2005/Atom"

register_namespace("content", CONTENT_NS)
register_namespace("atom", ATOM_NS)


def _visible_post_conditions() -> tuple:
    return visible_post_conditions()


def _is_post_public(post: BlogPost) -> bool:
    return is_post_public(post)


def _post_json_ld(request: Request, post: BlogPost) -> str:
    url = str(request.url_for("post_detail", post_id=post.slug or post.id))
    data = {
        "@context": "https://schema.org",
        "@type": "BlogPosting",
        "headline": post.title,
        "description": post.summary or post.title,
        "datePublished": post.published_at.isoformat(),
        "dateModified": post.updated_at.isoformat(),
        "inLanguage": "zh-CN",
        "author": {"@type": "Person", "name": AUTHOR_NAME},
        "publisher": {"@type": "Person", "name": AUTHOR_NAME},
        "mainEntityOfPage": {"@type": "WebPage", "@id": url},
        "url": url,
        "keywords": post.tags or [],
    }
    return json.dumps(data, ensure_ascii=False).replace("<", "\\u003c")


COMMENT_NOTICES = {
    "submitted": "评论已提交，审核通过后会显示。",
    "invalid": "评论内容不能为空。",
    "too_fast": "评论太快了，请 15 秒后再试。",
}


def _is_htmx(request: Request) -> bool:
    return request.headers.get("HX-Request") == "true"


def _hx_redirect(url: str) -> Response:
    return Response(status_code=200, headers={"HX-Redirect": url})


def _comment_notice(request: Request) -> str | None:
    return COMMENT_NOTICES.get(request.query_params.get("comment", ""))


def _comments_context(
    request: Request,
    db: Session,
    post: BlogPost,
    comment_page: int = 1,
    notice: str | None = None,
) -> dict:
    condition = (Comment.post_id == post.id, Comment.is_approved.is_(True))
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
    commenter, _, _ = current_commenter(request, db)
    return {
        "post": post,
        "comments": comments,
        "comment_total": comment_total,
        "comment_page": comment_page,
        "comment_total_pages": comment_total_pages,
        "comment_has_prev": comment_page > 1,
        "comment_has_next": comment_page < comment_total_pages,
        "commenter": commenter,
        "comment_notice": notice,
    }


def _comments_partial(
    request: Request, db: Session, post: BlogPost, notice: str | None
) -> Response:
    return templates.TemplateResponse(
        request=request,
        name="_comments.html",
        context=_comments_context(request, db, post, notice=notice),
    )


GUESTBOOK_NOTICES = {
    "submitted": "留言已提交。",
    "invalid": "留言内容不能为空。",
    "too_fast": "留言太快了，请 15 秒后再试。",
}


def _guestbook_notice(request: Request) -> str | None:
    return GUESTBOOK_NOTICES.get(request.query_params.get("message", ""))


def _guestbook_context(
    request: Request,
    db: Session,
    page: int = 1,
    notice: str | None = None,
) -> dict:
    total = db.scalar(select(func.count()).select_from(Message)) or 0
    total_pages = max((total + MESSAGES_PER_PAGE - 1) // MESSAGES_PER_PAGE, 1)
    page = min(max(page, 1), total_pages)
    messages = db.scalars(
        select(Message)
        .order_by(Message.created_at.desc(), Message.id.desc())
        .offset((page - 1) * MESSAGES_PER_PAGE)
        .limit(MESSAGES_PER_PAGE)
    ).all()
    return {
        "messages": messages,
        "user": getattr(request.state, "user", None),
        "total": total,
        "page": page,
        "total_pages": total_pages,
        "has_prev": page > 1,
        "has_next": page < total_pages,
        "guestbook_notice": notice,
    }


def _guestbook_partial(request: Request, db: Session, notice: str | None) -> Response:
    return templates.TemplateResponse(
        request=request,
        name="_guestbook_panel.html",
        context=_guestbook_context(request, db, notice=notice),
    )


MOMENT_NOTICES = {
    "submitted": "评论已提交，审核通过后会显示。",
    "invalid": "评论内容不能为空。",
    "too_fast": "评论太快了，请 15 秒后再试。",
}


def _moment_comments_context(
    request: Request,
    db: Session,
    moment: Moment,
    page: int = 1,
    notice: str | None = None,
) -> dict:
    condition = (
        MomentComment.moment_id == moment.id,
        MomentComment.is_approved.is_(True),
    )
    total_comments = (
        db.scalar(select(func.count()).select_from(MomentComment).where(*condition))
        or 0
    )
    approved_comments = db.scalars(
        select(MomentComment)
        .where(*condition)
        .order_by(MomentComment.created_at.desc(), MomentComment.id.desc())
        .limit(MOMENT_COMMENTS_SHOWN)
    ).all()
    commenter, _, _ = current_commenter(request, db)
    return {
        "moment": moment,
        "approved_comments": list(reversed(approved_comments)),
        "total_comments": total_comments,
        "commenter": commenter,
        "page": page,
        "moment_notice": notice,
    }


def _moment_comments_partial(
    request: Request,
    db: Session,
    moment: Moment,
    page: int,
    notice: str | None,
) -> Response:
    return templates.TemplateResponse(
        request=request,
        name="_moment_comments.html",
        context=_moment_comments_context(request, db, moment, page=page, notice=notice),
    )


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
    attach_sorted_tags(posts)
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
    post_id: str,
    db: DbSession,
    comment_page: int = Query(1, ge=1),
) -> Response:
    post = find_post(db, post_id)
    if post is None or (
        not _is_post_public(post) and current_admin(request, db) is None
    ):
        raise HTTPException(status_code=404, detail="文章不存在！")

    if post.slug and post_id != post.slug:
        target = request.url_for("post_detail", post_id=post.slug)
        suffix = f"?comment_page={comment_page}" if comment_page > 1 else ""
        return RedirectResponse(f"{target}{suffix}", status_code=301)

    attach_sorted_tags([post])
    previous_post, next_post = adjacent_posts(db, post)
    context = {
        "app_name": settings.app_name,
        "post": post,
        "post_json_ld": _post_json_ld(request, post),
        "toc": headings_for(post.content),
        "read_minutes": reading_minutes(post.content),
        "previous_post": previous_post,
        "next_post": next_post,
        "related_posts": related_posts(db, post),
    }
    context.update(
        _comments_context(
            request,
            db,
            post,
            comment_page=comment_page,
            notice=_comment_notice(request),
        )
    )
    return templates.TemplateResponse(
        request=request,
        name="post_detail.html",
        context=context,
    )


@router.post("/posts/{post_id}/comments")
def submit_comment(
    request: Request,
    db: DbSession,
    post_id: str,
    content: str = Form(..., max_length=2000),
    website: str = Form(""),
    _csrf: None = Depends(verify_csrf),
) -> Response:
    post = find_post(db, post_id)
    if post is None or (
        not _is_post_public(post) and current_admin(request, db) is None
    ):
        raise HTTPException(status_code=404, detail="文章不存在！")

    post_path = f"/posts/{post.slug or post.id}"
    author, actor_key, user_id = current_commenter(request, db)
    if author is None or actor_key is None:
        if _is_htmx(request):
            return _hx_redirect(f"/login?next={post_path}")
        return RedirectResponse(f"/login?next={post_path}", status_code=303)

    if website.strip():
        if _is_htmx(request):
            return _comments_partial(request, db, post, COMMENT_NOTICES["submitted"])
        return RedirectResponse(
            f"{post_path}?comment=submitted#comments", status_code=303
        )

    result = create_comment(db, post, author, actor_key, user_id, content)
    if _is_htmx(request):
        return _comments_partial(request, db, post, result.message)
    return RedirectResponse(
        f"{post_path}?comment={result.code}#comments", status_code=303
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

    commenter, _, _ = current_commenter(request, db)
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
) -> Response:
    moment = db.get(Moment, moment_id)
    if moment is None:
        raise HTTPException(status_code=404, detail="动态不存在！")

    author, actor_key, user_id = current_commenter(request, db)
    if author is None or actor_key is None:
        next_url = (
            f"/moments?page={page}#moment-{moment_id}"
            if page > 1
            else f"/moments#moment-{moment_id}"
        )
        login_url = f"/login?next={quote(next_url, safe='')}"
        if _is_htmx(request):
            return _hx_redirect(login_url)
        return RedirectResponse(login_url, status_code=303)

    target = request.url_for("moments_page")
    prefix = f"page={page}&comment=" if page > 1 else "comment="
    if website.strip():
        if _is_htmx(request):
            return _moment_comments_partial(
                request, db, moment, page, MOMENT_NOTICES["submitted"]
            )
        return RedirectResponse(
            f"{target}?{prefix}submitted#moment-{moment_id}", status_code=303
        )

    result = create_moment_comment(db, moment, author, actor_key, user_id, content)
    if _is_htmx(request):
        return _moment_comments_partial(request, db, moment, page, result.message)
    return RedirectResponse(
        f"{target}?{prefix}{result.code}#moment-{moment_id}",
        status_code=303,
    )


@router.get("/guestbook")
def guestbook_page(
    request: Request, db: DbSession, page: int = Query(1, ge=1)
) -> Response:
    context = _guestbook_context(
        request, db, page=page, notice=_guestbook_notice(request)
    )
    if page > context["total_pages"]:
        target = request.url_for("guestbook_page")
        return RedirectResponse(
            f"{target}?page={context['total_pages']}", status_code=303
        )

    return templates.TemplateResponse(
        request=request,
        name="guestbook.html",
        context={"app_name": settings.app_name, **context},
    )


@router.post("/guestbook")
def submit_message(
    request: Request,
    db: DbSession,
    content: str = Form(..., max_length=1000),
    website: str = Form(""),
    _csrf: None = Depends(verify_csrf),
) -> Response:
    user = getattr(request.state, "user", None)
    if user is None:
        if _is_htmx(request):
            return _hx_redirect("/login?next=/guestbook")
        return RedirectResponse("/login?next=/guestbook", status_code=303)

    target = request.url_for("guestbook_page")
    if website.strip():
        if _is_htmx(request):
            return _guestbook_partial(request, db, GUESTBOOK_NOTICES["submitted"])
        return RedirectResponse(f"{target}?message=submitted", status_code=303)

    result = create_message(db, user, content)
    if _is_htmx(request):
        return _guestbook_partial(request, db, result.message)
    return RedirectResponse(f"{target}?message={result.code}", status_code=303)


@router.get("/tags")
def tags_page(
    request: Request,
    db: DbSession,
    tag: str | None = Query(None),
    page: int = Query(1, ge=1),
) -> Response:
    if tag is None or tag == "":
        counts = visible_tag_counts(db)
        tags = sorted(counts.items(), key=tag_sort_key)
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
    attach_sorted_tags(posts)
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
        attach_sorted_tags(posts)
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
        link = str(request.url_for("post_detail", post_id=post.slug or post.id))
        SubElement(item, "link").text = link
        SubElement(item, "guid").text = link
        SubElement(item, "pubDate").text = format_datetime(
            datetime.combine(post.published_at, time.min).replace(tzinfo=site_zone())
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
                str(request.url_for("post_detail", post_id=post.slug or post.id)),
                post.updated_at.date().isoformat(),
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
        "Disallow: /api/\n"
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
