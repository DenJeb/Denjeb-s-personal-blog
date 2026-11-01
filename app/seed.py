"""
========== 开发用：把 sample_data 灌入数据库 ==========
"""

from datetime import date

from sqlalchemy import select

from app.db import SessionLocal
from app.markdown import render_markdown
from app.models import BlogPost
from app.sample_data import BLOG_POSTS


def seed() -> None:
    with SessionLocal() as db:
        if db.scalar(select(BlogPost.id).limit(1)) is not None:
            print("数据库已有数据，跳过。")
            return

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
        print(f"已写入 {len(BLOG_POSTS)} 篇博客。")


if __name__ == "__main__":
    seed()
