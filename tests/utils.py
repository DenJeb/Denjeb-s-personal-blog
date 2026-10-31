"""
========== 测试辅助函数 ==========
"""

import re


def csrf_token(html: str) -> str:
    match = re.search(r'name="csrf_token" value="([^"]+)"', html)
    assert match is not None, "页面中没有找到 csrf_token"
    return match.group(1)
