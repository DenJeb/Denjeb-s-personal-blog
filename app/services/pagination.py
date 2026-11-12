"""
========== 后台分页辅助 ==========
"""

ADMIN_PAGE_SIZE = 20


def page_slice(
    page: int, total: int, page_size: int = ADMIN_PAGE_SIZE
) -> tuple[int, int]:
    total_pages = max((total + page_size - 1) // page_size, 1)
    page = min(max(page, 1), total_pages)
    return page, total_pages
