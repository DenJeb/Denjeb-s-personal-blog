"""
========== CSRF 校验 ==========
"""

import secrets

from fastapi import Form, HTTPException, Request


def verify_csrf(request: Request, csrf_token: str = Form(...)) -> None:
    expected = request.session.get("csrf_token")
    if not expected or not secrets.compare_digest(expected, csrf_token):
        raise HTTPException(
            status_code=400,
            detail="CSRF 校验失败，请刷新页面后重试。",
        )
