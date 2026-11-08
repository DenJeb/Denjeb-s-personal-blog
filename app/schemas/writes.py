"""
========== 评论 / 动态评论 / 留言 API 模型 ==========
"""

from pydantic import BaseModel, Field


class PostCommentRequest(BaseModel):
    content: str = Field(max_length=2000)
    website: str = Field(default="", max_length=200)


class ContentRequest(BaseModel):
    content: str = Field(max_length=1000)
    website: str = Field(default="", max_length=200)


class WriteResponse(BaseModel):
    ok: bool
    message: str
