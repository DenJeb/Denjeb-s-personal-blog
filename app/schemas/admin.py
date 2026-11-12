"""
========== 后台 API 响应模型 ==========
"""

from datetime import date, datetime

from pydantic import BaseModel, Field

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


class AdminCommentItem(BaseModel):
    id: int
    post_id: int
    post_title: str
    post_slug: str | None
    author_name: str
    content: str
    created_at: datetime
    is_approved: bool


class AdminCommentList(BaseModel):
    items: list[AdminCommentItem]
    meta: PageMeta


class AdminMomentCommentItem(BaseModel):
    id: int
    moment_id: int
    moment_page: int
    author_name: str
    content: str
    created_at: datetime
    is_approved: bool


class AdminMomentCommentList(BaseModel):
    items: list[AdminMomentCommentItem]
    meta: PageMeta


class AdminMomentItem(BaseModel):
    id: int
    content: str
    created_at: datetime
    public_page: int


class AdminMomentList(BaseModel):
    items: list[AdminMomentItem]
    meta: PageMeta


class AdminMessageItem(BaseModel):
    id: int
    author_name: str
    content: str
    created_at: datetime


class AdminMessageList(BaseModel):
    items: list[AdminMessageItem]
    meta: PageMeta


class AdminUserItem(BaseModel):
    id: int
    email: str | None
    username: str
    is_active: bool
    created_at: datetime


class AdminUserList(BaseModel):
    items: list[AdminUserItem]
    meta: PageMeta


class AdminUploadItem(BaseModel):
    name: str
    url: str
    size: int
    referenced: bool


class AdminUploadList(BaseModel):
    items: list[AdminUploadItem]
    meta: PageMeta


class AdminInlineUpload(BaseModel):
    url: str
    markdown: str


class AdminSecurity(BaseModel):
    totp_enabled: bool
    setup_secret: str | None = None
    setup_uri: str | None = None


class AdminPostWriteRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    slug: str = Field(default="", max_length=200)
    summary: str = Field(default="", max_length=500)
    content: str = Field(min_length=1)
    published_at: date
    tags: list[str] = Field(default_factory=list)
    is_published: bool = False


class AdminMomentWriteRequest(BaseModel):
    content: str = Field(min_length=1, max_length=2000)


class AdminPreviewRequest(BaseModel):
    content: str


class AdminPreviewResponse(BaseModel):
    html: str


class AdminUploadDeleteRequest(BaseModel):
    path: str = Field(min_length=1, max_length=500)


class AdminTotpEnableRequest(BaseModel):
    code: str = Field(min_length=6, max_length=6)


class AdminTotpDisableRequest(BaseModel):
    password: str = Field(min_length=1, max_length=200)
    code: str = Field(min_length=6, max_length=6)


class AdminToggleResponse(BaseModel):
    ok: bool = True
    is_approved: bool | None = None
    is_active: bool | None = None


class AdminOkResponse(BaseModel):
    ok: bool = True
    message: str = ""
