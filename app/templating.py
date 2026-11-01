"""
========== 模板引擎 ==========
"""

import secrets
from pathlib import Path
from urllib.parse import parse_qsl, quote, urlencode, urlsplit, urlunsplit

from fastapi.templating import Jinja2Templates
from starlette.requests import Request

APP_DIR = Path(__file__).resolve().parent

templates = Jinja2Templates(directory=APP_DIR / "templates")

CANONICAL_QUERY_KEYS = {"page", "tag", "q", "comment_page"}


def _csrf_token(request: Request) -> str:
    token = request.session.get("csrf_token")
    if token is None:
        token = secrets.token_urlsafe(32)
        request.session["csrf_token"] = token
    return token


def _tag_url(tag: str, page: int | None = None) -> str:
    url = f"/tags?tag={quote(tag, safe='')}"
    if page is not None and page > 1:
        url += f"&page={page}"
    return url


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
templates.env.globals["canonical_url"] = _canonical_url
templates.env.globals["page_url"] = _page_url
