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
from app.models import (
    BlogPost,
    Comment,
    Message,
    Moment,
    MomentComment,
    User,
)
from app.services.uploads import delete_orphan_uploads

DEFAULT_PATH = PROJECT_DIR / "content" / "content-backup.json"


def _parse_created_at(value: str | None) -> datetime:
    return datetime.fromisoformat(value) if value else datetime.now(UTC)


def export_content(path: Path = DEFAULT_PATH) -> None:
    with SessionLocal() as db:
        posts = db.scalars(select(BlogPost).order_by(BlogPost.id)).all()
        comments = db.scalars(select(Comment).order_by(Comment.id)).all()
        moments = db.scalars(select(Moment).order_by(Moment.id)).all()
        moment_comments = db.scalars(
            select(MomentComment).order_by(MomentComment.id)
        ).all()
        messages = db.scalars(select(Message).order_by(Message.id)).all()

        data = {
            "exported_at": datetime.now(UTC).isoformat(),
            "posts": [
                {
                    "id": post.id,
                    "title": post.title,
                    "slug": post.slug,
                    "summary": post.summary,
                    "content": post.content,
                    "published_at": post.published_at.isoformat(),
                    "tags": post.tags or [],
                    "is_published": post.is_published,
                }
                for post in posts
            ],
            "comments": [
                {
                    "id": comment.id,
                    "post_id": comment.post_id,
                    "user_id": comment.user_id,
                    "author_name": comment.author_name,
                    "content": comment.content,
                    "is_approved": comment.is_approved,
                    "created_at": comment.created_at.isoformat(),
                }
                for comment in comments
            ],
            "moments": [
                {
                    "id": moment.id,
                    "content": moment.content,
                    "created_at": moment.created_at.isoformat(),
                }
                for moment in moments
            ],
            "moment_comments": [
                {
                    "id": comment.id,
                    "moment_id": comment.moment_id,
                    "user_id": comment.user_id,
                    "author_name": comment.author_name,
                    "content": comment.content,
                    "is_approved": comment.is_approved,
                    "created_at": comment.created_at.isoformat(),
                }
                for comment in moment_comments
            ],
            "messages": [
                {
                    "id": message.id,
                    "user_id": message.user_id,
                    "author_name": message.author_name,
                    "content": message.content,
                    "created_at": message.created_at.isoformat(),
                }
                for message in messages
            ],
        }

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"已导出 {len(data['posts'])} 篇文章、"
        f"{len(data['comments'])} 条评论、"
        f"{len(data['moments'])} 条动态、"
        f"{len(data['moment_comments'])} 条动态评论、"
        f"{len(data['messages'])} 条留言 -> {path}"
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
            db.execute(delete(MomentComment))
            db.execute(delete(Moment))
            db.execute(delete(Message))
            db.execute(delete(Comment))
            db.execute(delete(BlogPost))
            db.flush()

            existing_user_ids = set(db.scalars(select(User.id)).all())

            for item in data.get("posts", []):
                content = item["content"]
                db.add(
                    BlogPost(
                        id=item["id"],
                        title=item["title"],
                        slug=item.get("slug") or f"post-{item['id']}",
                        summary=item.get("summary", ""),
                        content=content,
                        content_html=render_markdown(content),
                        published_at=date.fromisoformat(item["published_at"]),
                        tags=item.get("tags", []),
                        is_published=item.get("is_published", True),
                    )
                )

            for item in data.get("moments", []):
                db.add(
                    Moment(
                        id=item["id"],
                        content=item["content"],
                        created_at=_parse_created_at(item.get("created_at")),
                    )
                )

            db.flush()

            for item in data.get("comments", []):
                user_id = item.get("user_id")
                db.add(
                    Comment(
                        id=item["id"],
                        post_id=item["post_id"],
                        user_id=(user_id if user_id in existing_user_ids else None),
                        author_name=item["author_name"],
                        content=item["content"],
                        is_approved=item.get("is_approved", False),
                        created_at=_parse_created_at(item.get("created_at")),
                    )
                )

            for item in data.get("moment_comments", []):
                user_id = item.get("user_id")
                db.add(
                    MomentComment(
                        id=item["id"],
                        moment_id=item["moment_id"],
                        user_id=(user_id if user_id in existing_user_ids else None),
                        author_name=item["author_name"],
                        content=item["content"],
                        is_approved=item.get("is_approved", False),
                        created_at=_parse_created_at(item.get("created_at")),
                    )
                )

            for item in data.get("messages", []):
                user_id = item.get("user_id")
                db.add(
                    Message(
                        id=item["id"],
                        user_id=(user_id if user_id in existing_user_ids else None),
                        author_name=item["author_name"],
                        content=item["content"],
                        created_at=_parse_created_at(item.get("created_at")),
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
        f"已恢复 {len(data.get('posts', []))} 篇文章、"
        f"{len(data.get('comments', []))} 条评论、"
        f"{len(data.get('moments', []))} 条动态、"
        f"{len(data.get('moment_comments', []))} 条动态评论、"
        f"{len(data.get('messages', []))} 条留言 <- {path}"
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
        help="确认覆盖现有文章、动态、评论和留言",
    )
    import_parser.add_argument(
        "--clean-uploads",
        action="store_true",
        help="导入成功后删除没有被文章引用的图片",
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
