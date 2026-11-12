"""
========== 应用入口 ==========
"""

import logging
import secrets
from pathlib import Path

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.config import settings
from app.current_user import CurrentUserMiddleware
from app.db import engine
from app.routers import account, admin, api, public
from app.templating import templates

APP_DIR = Path(__file__).resolve().parent
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    openapi_url="/openapi.json" if settings.debug else None,
)

app.add_middleware(CurrentUserMiddleware)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.secret_key,
    session_cookie=(
        "__Host-blog_session" if settings.session_https_only else "blog_session"
    ),
    max_age=14 * 24 * 3600,
    same_site="lax",
    https_only=settings.session_https_only,
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.trusted_hosts_list,
)

app.mount("/static", StaticFiles(directory=APP_DIR / "static"), name="static")

app.include_router(api.router)
app.include_router(public.router)
app.include_router(account.router)
app.include_router(admin.router)


PRIVATE_PATH_PREFIXES = (
    "/admin",
    "/account",
    "/login",
    "/register",
    "/forgot-password",
    "/reset-password",
    "/api/v1/auth",
    "/api/v1/admin",
)

LEGACY_PUBLIC_PREFIXES = (
    "/posts",
    "/moments",
    "/guestbook",
    "/tags",
    "/archive",
    "/search",
    "/about",
)


def _is_legacy_public_path(path: str) -> bool:
    if path == "/":
        return True
    return any(
        path == prefix or path.startswith(f"{prefix}/")
        for prefix in LEGACY_PUBLIC_PREFIXES
    )


@app.middleware("http")
async def block_legacy_public_site(request: Request, call_next):
    if not settings.legacy_public_site_enabled and _is_legacy_public_path(
        request.url.path
    ):
        return Response(content="Not Found", status_code=404, media_type="text/plain")
    return await call_next(request)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    nonce = secrets.token_urlsafe(16)
    request.state.csp_nonce = nonce
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault(
        "Permissions-Policy",
        "geolocation=(), microphone=(), camera=()",
    )
    if settings.session_https_only:
        response.headers.setdefault(
            "Strict-Transport-Security",
            "max-age=31536000; includeSubDomains",
        )
    response.headers.setdefault(
        "Content-Security-Policy",
        f"default-src 'self'; script-src 'self' 'nonce-{nonce}'; "
        "style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; "
        "font-src 'self' data:; object-src 'none'; base-uri 'self'; "
        "form-action 'self'; frame-ancestors 'none'",
    )
    if request.url.path.startswith(PRIVATE_PATH_PREFIXES):
        response.headers.setdefault("Cache-Control", "no-store")
    return response


@app.get("/healthz", include_in_schema=False)
def healthz():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception:
        return JSONResponse({"status": "error"}, status_code=503)
    return {"status": "ok"}


JSON_ERROR_PATHS = ("/admin/uploads/inline",)


def _is_api_request(request: Request) -> bool:
    return request.url.path.startswith("/api/") or request.url.path in JSON_ERROR_PATHS


@app.exception_handler(StarletteHTTPException)
async def http_exception(request: Request, exc: StarletteHTTPException):
    if exc.status_code in {204, 304}:
        return Response(status_code=exc.status_code, headers=exc.headers)
    if 300 <= exc.status_code < 400:
        headers = exc.headers or {}
        location = headers.get("Location") or headers.get("location") or "/"
        return RedirectResponse(location, status_code=exc.status_code)
    if _is_api_request(request):
        return JSONResponse(
            {"detail": exc.detail},
            status_code=exc.status_code,
            headers=exc.headers,
        )
    detail = exc.detail if isinstance(exc.detail, str) else "请求失败"
    return templates.TemplateResponse(
        request=request,
        name="error.html",
        context={
            "app_name": settings.app_name,
            "status_code": exc.status_code,
            "detail": detail,
        },
        status_code=exc.status_code,
        headers=exc.headers,
    )


@app.exception_handler(404)
async def not_found(request: Request, exc: StarletteHTTPException):
    if _is_api_request(request):
        return JSONResponse({"detail": exc.detail}, status_code=404)
    return templates.TemplateResponse(
        request=request,
        name="404.html",
        context={"app_name": settings.app_name},
        status_code=404,
    )


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError):
    if _is_api_request(request):
        return JSONResponse({"detail": "请求参数不正确"}, status_code=422)
    return templates.TemplateResponse(
        request=request,
        name="422.html",
        context={"app_name": settings.app_name},
        status_code=422,
    )


@app.exception_handler(Exception)
async def server_error(request: Request, exc: Exception):
    logger.error(
        "Unhandled error on %s",
        request.url.path,
        exc_info=(type(exc), exc, exc.__traceback__),
    )
    if _is_api_request(request):
        return JSONResponse({"detail": "服务器内部错误"}, status_code=500)
    return templates.TemplateResponse(
        request=request,
        name="500.html",
        context={"app_name": settings.app_name},
        status_code=500,
    )
