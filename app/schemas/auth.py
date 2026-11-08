"""
========== 认证 API 请求/响应模型 ==========
"""

from pydantic import BaseModel, Field


class CurrentUser(BaseModel):
    name: str


class CurrentUserResponse(BaseModel):
    user: CurrentUser | None


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=200)


class CsrfResponse(BaseModel):
    csrf_token: str


class LogoutResponse(BaseModel):
    ok: bool
