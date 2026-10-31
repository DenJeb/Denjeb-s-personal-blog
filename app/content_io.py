"""
========== 内容备份与恢复 ==========
"""

import argparse
import json
from datetime import UTC, date, datetime
from pathlib import Path

from sqlalchemy import delete, select

from app.config import PROJECT_DIR
from app.db import SessionLocal
from app.markdown import render_markdown
from app.models import BlogPost, Category, Comment, Note
from app.routers.admin.common import delete_orphan_uploads

DEFAULT_PATH = PROJECT_DIR / "content" / "content-backup.json"


def export_content(path: Path = DEFAULT_PATH) -> None:
    with SessionLocal() as db:
        categories = db.scalars(select(Category).order_by(Category.id)).all()
        posts = db.scalars(select(BlogPost).order_by(BlogPost.id)).all()
        notes = db.scalars(select(Note).order_by(Note.id)).all()
        comments = db.scalars(select(Comment).order_by(Comment.id)).all()
        category_slugs = {category.id: category.slug for category in categories}

        data = {
            "exported_at": datetime.now(UTC).isoformat(),
            "categories": [
                {
                    "id": category.id,
                    "slug": category.slug,
                    "name": category.name,
                }
                for category in categories
            ],
            "posts": [
                {
                    "id": post.id,
                    "title": post.title,
                    "summary": post.summary,
                    "content": post.content,
                    "published_at": post.published_at.isoformat(),
                    "tags": post.tags or [],
                    "is_published": post.is_published,
                }
                for post in posts
            ],
            "notes": [
                {
                    "id": note.id,
                    "title": note.title,
                    "summary": note.summary,
                    "content": note.content,
                    "published_at": note.published_at.isoformat(),
                    "tags": note.tags or [],
                    "category_slug": category_slugs.get(note.category_id),
                }
                for note in notes
            ],
            "comments": [
                {
                    "id": comment.id,
                    "post_id": comment.post_id,
                    "author_name": comment.author_name,
                    "content": comment.content,
                    "is_approved": comment.is_approved,
                    "created_at": comment.created_at.isoformat(),
                }
                for comment in comments
            ],
        }

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"已导出 {len(data['categories'])} 个分类、"
        f"{len(data['posts'])} 篇文章、{len(data['notes'])} 篇笔记、"
        f"{len(data['comments'])} 条评论 -> {path}"
    )


def import_content(
    path: Path = DEFAULT_PATH,
    replace: bool = False,
    clean_uploads: bool = False,
) -> None:
    if not replace:
        raise SystemExit("导入会覆盖现有内容，请加 --replace。")
    if not path.is_file():
        raise SystemExit(f"找不到备份文件：{path}")

    data = json.loads(path.read_text(encoding="utf-8"))

    with SessionLocal() as db:
        try:
            db.execute(delete(Comment))
            db.execute(delete(Note))
            db.execute(delete(BlogPost))
            db.execute(delete(Category))
            db.flush()

            categories: dict[str, Category] = {}
            for item in data.get("categories", []):
                category = Category(
                    id=item["id"],
                    slug=item["slug"],
                    name=item["name"],
                )
                db.add(category)
                categories[item["slug"]] = category
            db.flush()

            for item in data.get("posts", []):
                content = item["content"]
                db.add(
                    BlogPost(
                        id=item["id"],
                        title=item["title"],
                        summary=item.get("summary", ""),
                        content=content,
                        content_html=render_markdown(content),
                        published_at=date.fromisoformat(item["published_at"]),
                        tags=item.get("tags", []),
                        is_published=item.get("is_published", True),
                    )
                )

            for item in data.get("notes", []):
                category = categories.get(item["category_slug"])
                if category is None:
                    raise ValueError(
                        f"笔记《{item['title']}》的分类不存在："
                        f"{item['category_slug']}"
                    )
                content = item["content"]
                db.add(
                    Note(
                        id=item["id"],
                        title=item["title"],
                        summary=item.get("summary", ""),
                        content=content,
                        content_html=render_markdown(content),
                        published_at=date.fromisoformat(item["published_at"]),
                        tags=item.get("tags", []),
                        category_id=category.id,
                    )
                )

            db.flush()

            for item in data.get("comments", []):
                created_at = item.get("created_at")
                db.add(
                    Comment(
                        id=item["id"],
                        post_id=item["post_id"],
                        author_name=item["author_name"],
                        content=item["content"],
                        is_approved=item.get("is_approved", False),
                        created_at=(
                            datetime.fromisoformat(created_at)
                            if created_at
                            else datetime.now(UTC)
                        ),
                    )
                )

            db.commit()
        except Exception:
            db.rollback()
            raise

    if clean_uploads:
        with SessionLocal() as db:
            delete_orphan_uploads(db)

    print(
        f"已恢复 {len(data.get('categories', []))} 个分类、"
        f"{len(data.get('posts', []))} 篇文章、"
        f"{len(data.get('notes', []))} 篇笔记、"
        f"{len(data.get('comments', []))} 条评论 <- {path}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="导出/恢复博客内容")
    subparsers = parser.add_subparsers(dest="command", required=True)

    export_parser = subparsers.add_parser("export", help="导出内容到 JSON")
    export_parser.add_argument("path", nargs="?", default=str(DEFAULT_PATH))

    import_parser = subparsers.add_parser("import", help="从 JSON 恢复内容")
    import_parser.add_argument("path", nargs="?", default=str(DEFAULT_PATH))
    import_parser.add_argument(
        "--replace",
        action="store_true",
        help="确认覆盖现有文章、笔记、评论和分类",
    )
    import_parser.add_argument(
        "--clean-uploads",
        action="store_true",
        help="导入成功后删除没有被文章或笔记引用的图片",
    )

    args = parser.parse_args()
    if args.command == "export":
        export_content(Path(args.path))
    else:
        import_content(
            Path(args.path),
            replace=args.replace,
            clean_uploads=args.clean_uploads,
        )


if __name__ == "__main__":
    main()
