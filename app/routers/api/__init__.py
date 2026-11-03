"""
========== JSON API 路由 ==========
"""

from fastapi import APIRouter

from app.routers.api import public

router = APIRouter(prefix="/api/v1")
router.include_router(public.router)
