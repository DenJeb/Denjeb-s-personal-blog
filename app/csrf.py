"""
========== CSRF 校验 ==========
"""

import secrets

from fastapi import Form, Header, HTTPException, Request

CSRF_SESSION_KEY = "csrf_token"


def get_csrf_token(request: Request) -> str:
    """Return the session CSRF token, minting one if needed."""
    token = request.session.get(CSRF_SESSION_KEY)
    if token is None:
        token = secrets.token_urlsafe(32)
        request.session[CSRF_SESSION_KEY] = token
    return token


def _check(request: Request, submitted: str | None) -> None:
    expected = request.session.get(CSRF_SESSION_KEY)
    if not expected or not submitted or not secrets.compare_digest(expected, submitted):
        raise HTTPException(
            status_code=400,
            detail="CSRF 校验失败，请刷新页面后重试。",
        )


def verify_csrf(request: Request, csrf_token: str = Form(...)) -> None:
    _check(request, csrf_token)


def verify_csrf_header(
    request: Request,
    x_csrf_token: str | None = Header(None, alias="X-CSRF-Token"),
) -> None:
    _check(request, x_csrf_token)
