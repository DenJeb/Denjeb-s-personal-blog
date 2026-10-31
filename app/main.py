"""
========== 应用入口 ==========
"""

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.config import settings
from app.current_user import CurrentUserMiddleware
from app.db import engine
from app.routers import account, admin, public
from app.templating import templates

APP_DIR = Path(__file__).resolve().parent

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
    session_cookie="blog_session",
    max_age=14 * 24 * 3600,
    same_site="lax",
    https_only=settings.session_https_only,
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.trusted_hosts_list,
)

app.mount("/static", StaticFiles(directory=APP_DIR / "static"), name="static")

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
)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault(
        "Permissions-Policy",
        "geolocation=(), microphone=(), camera=()",
    )
    response.headers.setdefault(
        "Content-Security-Policy",
        "default-src 'self'; script-src 'self' 'unsafe-inline'; "
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


@app.exception_handler(404)
async def not_found(request: Request, exc: StarletteHTTPException):
    return templates.TemplateResponse(
        request=request,
        name="404.html",
        context={"app_name": settings.app_name},
        status_code=404,
    )


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError):
    return templates.TemplateResponse(
        request=request,
        name="422.html",
        context={"app_name": settings.app_name},
        status_code=422,
    )


@app.exception_handler(Exception)
async def server_error(request: Request, exc: Exception):
    return templates.TemplateResponse(
        request=request,
        name="500.html",
        context={"app_name": settings.app_name},
        status_code=500,
    )
