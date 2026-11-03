"""
========== 公开 API 响应模型 ==========
"""

from datetime import date, datetime

from pydantic import BaseModel


class PageMeta(BaseModel):
    page: int
    per_page: int
    total: int
    total_pages: int
    has_prev: bool
    has_next: bool


class PostSummary(BaseModel):
    id: int
    title: str
    slug: str
    url: str
    summary: str
    published_at: date
    tags: list[str]
    reading_minutes: int


class PostLink(BaseModel):
    title: str
    slug: str
    url: str
    published_at: date


class TocItem(BaseModel):
    level: int
    text: str
    id: str


class PostDetail(PostSummary):
    content: str
    content_html: str
    toc: list[TocItem]
    previous_post: PostLink | None = None
    next_post: PostLink | None = None
    related_posts: list[PostSummary]


class PostListResponse(BaseModel):
    items: list[PostSummary]
    meta: PageMeta


class TagItem(BaseModel):
    name: str
    count: int


class TagListResponse(BaseModel):
    items: list[TagItem]


class ArchiveMonth(BaseModel):
    month: int
    posts: list[PostSummary]


class ArchiveYear(BaseModel):
    year: int
    months: list[ArchiveMonth]


class ArchiveResponse(BaseModel):
    total: int
    years: list[ArchiveYear]


class CommentItem(BaseModel):
    id: int
    author_name: str
    content: str
    created_at: datetime


class CommentListResponse(BaseModel):
    items: list[CommentItem]
    meta: PageMeta


class MomentCommentItem(CommentItem):
    pass


class MomentItem(BaseModel):
    id: int
    content: str
    created_at: datetime
    comment_count: int
    comments: list[MomentCommentItem]


class MomentListResponse(BaseModel):
    items: list[MomentItem]
    meta: PageMeta


class MessageItem(BaseModel):
    id: int
    author_name: str
    content: str
    created_at: datetime


class MessageListResponse(BaseModel):
    items: list[MessageItem]
    meta: PageMeta


class SiteInfo(BaseModel):
    app_name: str
    author: str
    site_url: str
