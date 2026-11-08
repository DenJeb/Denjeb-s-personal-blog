"""
Phase 2 live E2E helper: set up / verify a disposable SQLite database.

Usage (from the repo root, with the venv active):

    DATABASE_URL=sqlite:///F:/path/to/project/.e2e-blog.db \
        python scripts/e2e_phase2.py setup

    DATABASE_URL=... python scripts/e2e_phase2.py verify

The setup writes .e2e-blog.json with the test user / post slug. The caller
should delete .e2e-blog.db and .e2e-blog.json after the run.
"""

import json
import os
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

E2E_EMAIL = "e2e@example.com"
E2E_USERNAME = "e2e_user"
E2E_PASSWORD = "E2ePass123!"
E2E_MOMENT = "E2E 动态"
E2E_MARKER = "真实 E2E "


def _require_database_url() -> None:
    if not os.environ.get("DATABASE_URL"):
        raise SystemExit("DATABASE_URL is required")


def setup() -> None:
    _require_database_url()

    from alembic import command
    from alembic.config import Config
    from pwdlib import PasswordHash
    from sqlalchemy import delete, select

    from app.config import PROJECT_DIR
    from app.db import SessionLocal
    from app.models import BlogPost, Moment, User

    command.upgrade(Config(str(PROJECT_DIR / "alembic.ini")), "head")

    from app.seed import seed

    seed()

    with SessionLocal() as db:
        db.execute(delete(User).where(User.email == E2E_EMAIL))
        db.execute(delete(User).where(User.username == E2E_USERNAME))
        db.execute(delete(Moment).where(Moment.content == E2E_MOMENT))
        db.add(
            User(
                email=E2E_EMAIL,
                username=E2E_USERNAME,
                password_hash=PasswordHash.recommended().hash(E2E_PASSWORD),
            )
        )
        db.add(Moment(content=E2E_MOMENT))
        db.commit()

        post = db.scalar(
            select(BlogPost)
            .where(
                BlogPost.is_published.is_(True),
                BlogPost.published_at <= date.today(),
            )
            .order_by(BlogPost.published_at.desc())
            .limit(1)
        )
        if post is None:
            raise SystemExit("no public post found for E2E")

        info = {
            "email": E2E_EMAIL,
            "username": E2E_USERNAME,
            "password": E2E_PASSWORD,
            "post_slug": post.slug or str(post.id),
        }

    (ROOT / ".e2e-blog.json").write_text(
        json.dumps(info, ensure_ascii=False), encoding="utf-8"
    )
    print(json.dumps(info, ensure_ascii=False))


def verify() -> None:
    _require_database_url()

    from sqlalchemy import func, select

    from app.db import SessionLocal
    from app.models import Comment, Message, MomentComment

    with SessionLocal() as db:
        result = {
            "comments": db.scalar(
                select(func.count())
                .select_from(Comment)
                .where(Comment.content.like(f"{E2E_MARKER}%"))
            )
            or 0,
            "moment_comments": db.scalar(
                select(func.count())
                .select_from(MomentComment)
                .where(MomentComment.content.like(f"{E2E_MARKER}%"))
            )
            or 0,
            "messages": db.scalar(
                select(func.count())
                .select_from(Message)
                .where(Message.content.like(f"{E2E_MARKER}%"))
            )
            or 0,
        }

    print(json.dumps(result, ensure_ascii=False))
    if min(result.values()) < 1:
        raise SystemExit("E2E writes were not all persisted")


if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else "setup"
    if action == "setup":
        setup()
    elif action == "verify":
        verify()
    else:
        raise SystemExit("usage: python scripts/e2e_phase2.py [setup|verify]")
