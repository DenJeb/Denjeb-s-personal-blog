"""
========== 站点时区测试 ==========
"""

from app.config import settings
from app.time_utils import mysql_timezone_offset, site_now, site_today


def test_site_timezone_offset(monkeypatch):
    monkeypatch.setattr(settings, "site_timezone", "Asia/Shanghai")

    assert site_now().utcoffset().total_seconds() == 8 * 3600
    assert site_today() == site_now().date()
    assert mysql_timezone_offset() == "+08:00"


def test_unknown_timezone_falls_back_to_utc(monkeypatch):
    monkeypatch.setattr(settings, "site_timezone", "Not/AZone")

    assert site_now().utcoffset().total_seconds() == 0
    assert mysql_timezone_offset() == "+00:00"
