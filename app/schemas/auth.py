"""
========== 认证 API 响应模型 ==========
"""

from pydantic import BaseModel


class CurrentUser(BaseModel):
    name: str


class CurrentUserResponse(BaseModel):
    user: CurrentUser | None
