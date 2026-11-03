"""
========== 测试辅助函数 ==========
"""

import re
from io import BytesIO

from PIL import Image


def csrf_token(html: str) -> str:
    match = re.search(r'name="csrf_token" value="([^"]+)"', html)
    assert match is not None, "页面中没有找到 csrf_token"
    return match.group(1)


def image_bytes(
    size: tuple[int, int] = (10, 10),
    fmt: str = "PNG",
    color: tuple[int, int, int] = (255, 0, 0),
) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", size, color).save(buffer, format=fmt)
    return buffer.getvalue()
