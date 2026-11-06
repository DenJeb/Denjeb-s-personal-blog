"""
========== JSON API 路由 ==========
"""

from fastapi import APIRouter

from app.routers.api import auth, public

router = APIRouter(prefix="/api/v1")
router.include_router(public.router)
router.include_router(auth.router)
