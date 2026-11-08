"""
========== 模板引擎 ==========
"""

from pathlib import Path
from urllib.parse import parse_qsl, quote, urlencode, urlsplit, urlunsplit

from fastapi.templating import Jinja2Templates
from starlette.requests import Request

from app.csrf import get_csrf_token
from app.services.content import reading_minutes

APP_DIR = Path(__file__).resolve().parent

templates = Jinja2Templates(directory=APP_DIR / "templates")

CANONICAL_QUERY_KEYS = {"page", "tag", "q", "comment_page"}


def _csrf_token(request: Request) -> str:
    return get_csrf_token(request)


def _tag_url(tag: str, page: int | None = None) -> str:
    url = f"/tags?tag={quote(tag, safe='')}"
    if page is not None and page > 1:
        url += f"&page={page}"
    return url


def _post_path(post) -> str:
    return f"/posts/{post.slug or post.id}"


def _canonical_url(request: Request) -> str:
    parts = urlsplit(str(request.url))
    query = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if key in CANONICAL_QUERY_KEYS
        and not (key in {"page", "comment_page"} and value == "1")
    ]
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), ""))


def _page_url(request: Request, page: int, param: str = "page") -> str:
    parts = urlsplit(str(request.url))
    query = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if key != param
    ]
    if page > 1:
        query.append((param, str(page)))
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), ""))


templates.env.globals["csrf_token"] = _csrf_token
templates.env.globals["tag_url"] = _tag_url
templates.env.globals["post_path"] = _post_path
templates.env.globals["reading_minutes"] = reading_minutes
templates.env.globals["canonical_url"] = _canonical_url
templates.env.globals["page_url"] = _page_url
