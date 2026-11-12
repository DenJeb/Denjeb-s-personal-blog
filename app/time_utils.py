"""
========== 站点时区工具 ==========

数据库里的内容时间统一按站点时区保存（默认 Asia/Shanghai），
跨时区访问时前端直接显示站点时间，不做二次换算。
"""

from datetime import UTC, date, datetime, timedelta, tzinfo
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.config import settings


def site_zone() -> tzinfo:
    try:
        return ZoneInfo(settings.site_timezone)
    except ZoneInfoNotFoundError:
        # Windows 本地环境没有 tzdata 时退回 UTC，生产 Linux 不受影响。
        return UTC


def site_now() -> datetime:
    return datetime.now(site_zone())


def site_now_naive() -> datetime:
    return site_now().replace(tzinfo=None)


def site_today() -> date:
    return site_now().date()


def mysql_timezone_offset() -> str:
    """把当前站点时区转换成 MySQL 可用的 +HH:MM 偏移。"""
    offset = site_now().utcoffset() or timedelta(0)
    total_seconds = int(offset.total_seconds())
    sign = "+" if total_seconds >= 0 else "-"
    total_seconds = abs(total_seconds)
    hours, remainder = divmod(total_seconds, 3600)
    minutes = remainder // 60
    return f"{sign}{hours:02d}:{minutes:02d}"
