"""
========== 临时假数据 ==========
"""

CATEGORIES = [
    {"slug": "cpp", "name": "C++ 篇"},
    {"slug": "python", "name": "Python 篇"},
    {"slug": "data-structures", "name": "数据结构"},
    {"slug": "mysql", "name": "MySQL"},
    {"slug": "network", "name": "计算机网络"},
    {"slug": "linux", "name": "操作系统"},
]

CATEGORY_MAP = {category["slug"]: category["name"] for category in CATEGORIES}

NOTES = [
    {
        "id": 1,
        "title": "C++ 面向对象编程",
        "summary": "类、对象、封装、继承和多态的学习笔记。",
        "content": "这里是正文占位内容。阶段 1 先用纯文本，阶段 3 再接入 Markdown 渲染。",
        "category_slug": "cpp",
        "published_at": "2026-10-20",
        "tags": ["C++", "OOP"],
    },
    {
        "id": 2,
        "title": "C++ STL",
        "summary": "容器、迭代器、算法和函数对象。",
        "content": "这里是正文占位内容。",
        "category_slug": "cpp",
        "published_at": "2026-10-18",
        "tags": ["C++", "STL"],
    },
    {
        "id": 3,
        "title": "MySQL 索引结构",
        "summary": "B+ 树、聚簇索引与回表。",
        "content": "这里是正文占位内容。",
        "category_slug": "mysql",
        "published_at": "2026-10-15",
        "tags": ["MySQL", "索引"],
    },
]

BLOG_POSTS = [
    {
        "id": 1,
        "title": "博客开张：为什么用 FastAPI + Jinja2",
        "summary": "记录搭建这个博客的起点和技术选型。",
        "content": "这里是正文占位内容。阶段 3 会接入 Markdown 渲染。",
        "published_at": "2026-10-26",
        "tags": ["FastAPI", "博客"],
    },
    {
        "id": 2,
        "title": "我的学习路线整理",
        "summary": "C++、Python、数据结构、MySQL 的后续计划。",
        "content": "这里是正文占位内容。",
        "published_at": "2026-10-24",
        "tags": ["学习"],
    },
]
