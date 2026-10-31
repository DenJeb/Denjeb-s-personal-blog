"""
========== 后台路由 ==========
"""

from fastapi import APIRouter

from app.routers.admin import (
    auth,
    categories,
    comments,
    dashboard,
    notes,
    posts,
    uploads,
    users,
)

router = APIRouter(prefix="/admin")
router.include_router(auth.router)
router.include_router(dashboard.router)
router.include_router(posts.router)
router.include_router(notes.router)
router.include_router(categories.router)
router.include_router(comments.router)
router.include_router(uploads.router)
router.include_router(users.router)
