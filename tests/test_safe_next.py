"""
========== 登录 next 参数安全测试 ==========
"""

from app.services.accounts import safe_next


def test_safe_next_keeps_internal_paths():
    assert safe_next("/posts") == "/posts"
    assert safe_next("/posts?page=2#comments") == "/posts?page=2#comments"


def test_safe_next_rejects_external_and_control_chars():
    assert safe_next("https://evil.com") == "/"
    assert safe_next("//evil.com") == "/"
    assert safe_next("/\\evil.com") == "/"
    assert safe_next("/posts\n") == "/"
