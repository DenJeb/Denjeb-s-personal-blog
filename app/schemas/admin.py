"""
========== 后台 API 响应模型 ==========
"""

from datetime import date

from pydantic import BaseModel

from app.schemas.public import PageMeta


class AdminMe(BaseModel):
    username: str
    email: str | None = None


class AdminDashboard(BaseModel):
    post_count: int
    moment_count: int
    message_count: int
    comment_count: int
    moment_comment_count: int
    user_count: int
    pending_count: int
    moment_pending_count: int


class AdminPostSummary(BaseModel):
    id: int
    title: str
    slug: str | None
    summary: str
    published_at: date
    is_published: bool
    is_public: bool
    tags: list[str]
    reading_minutes: int


class AdminPostList(BaseModel):
    items: list[AdminPostSummary]
    meta: PageMeta


class AdminPostDetail(AdminPostSummary):
    content: str
    content_html: str | None = None
