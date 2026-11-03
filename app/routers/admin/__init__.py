"""
========== 后台路由 ==========
"""

from fastapi import APIRouter

from app.routers.admin import (
    auth,
    comments,
    dashboard,
    editor,
    messages,
    moment_comments,
    moments,
    posts,
    security,
    uploads,
    users,
)

router = APIRouter(prefix="/admin")
router.include_router(auth.router)
router.include_router(dashboard.router)
router.include_router(posts.router)
router.include_router(editor.router)
router.include_router(comments.router)
router.include_router(moments.router)
router.include_router(moment_comments.router)
router.include_router(messages.router)
router.include_router(uploads.router)
router.include_router(users.router)
router.include_router(security.router)
