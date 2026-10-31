"""
========== 开发用：把 sample_data 灌入数据库 ==========
"""

from datetime import date

from sqlalchemy import select

from app.db import SessionLocal
from app.markdown import render_markdown
from app.models import BlogPost, Category, Note
from app.sample_data import BLOG_POSTS, CATEGORIES, NOTES


def seed() -> None:
    with SessionLocal() as db:
        if db.scalar(select(Category.id).limit(1)) is not None:
            print("数据库已有数据，跳过。")
            return

        categories = {}
        for item in CATEGORIES:
            category = Category(slug=item["slug"], name=item["name"])
            db.add(category)
            categories[item["slug"]] = category

        db.flush()  # 先拿到自增 id

        for item in NOTES:
            db.add(
                Note(
                    title=item["title"],
                    summary=item["summary"],
                    content=item["content"],
                    content_html=render_markdown(item["content"]),
                    published_at=date.fromisoformat(item["published_at"]),
                    tags=item["tags"],
                    category_id=categories[item["category_slug"]].id,
                )
            )

        for item in BLOG_POSTS:
            db.add(
                BlogPost(
                    title=item["title"],
                    summary=item["summary"],
                    content=item["content"],
                    content_html=render_markdown(item["content"]),
                    published_at=date.fromisoformat(item["published_at"]),
                    tags=item["tags"],
                )
            )

        db.commit()
        print(
            f"已写入 {len(categories)} 个分类、"
            f"{len(NOTES)} 篇笔记、{len(BLOG_POSTS)} 篇博客。"
        )


if __name__ == "__main__":
    seed()
