"""
========== URL slug 生成 ==========
"""

from slugify import slugify

MAX_SLUG_LENGTH = 200


def slugify_text(value: str, fallback: str = "post") -> str:
    return (slugify(value) or fallback)[:MAX_SLUG_LENGTH]
