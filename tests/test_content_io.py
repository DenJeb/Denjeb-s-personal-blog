"""
========== 内容导出测试 ==========
"""

import json

from sqlalchemy import delete, select

from app.content_io import export_content, import_content
from app.db import SessionLocal
from app.models import Message, Moment, MomentComment, User


def test_export_content(tmp_path):
    path = tmp_path / "backup.json"
    export_content(path)

    data = json.loads(path.read_text(encoding="utf-8"))
    assert "categories" not in data
    assert "notes" not in data
    assert len(data["posts"]) >= 1
    assert "content" in data["posts"][0]
    assert "is_published" in data["posts"][0]
    assert isinstance(data["comments"], list)
    assert "password" not in json.dumps(data).lower()


def test_export_includes_new_content(tmp_path, user_client):
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.username == "__pytest_user__"))
        assert user is not None
        moment = Moment(content="__pytest_export_moment__")
        db.add(moment)
        db.flush()
        db.add(
            MomentComment(
                moment_id=moment.id,
                user_id=user.id,
                author_name=user.username,
                content="__pytest_export_moment_comment__",
                is_approved=True,
            )
        )
        db.add(
            Message(
                user_id=user.id,
                author_name=user.username,
                content="__pytest_export_message__",
            )
        )
        db.commit()

    path = tmp_path / "backup.json"
    export_content(path)
    data = json.loads(path.read_text(encoding="utf-8"))

    assert any(
        item["content"] == "__pytest_export_moment__" for item in data["moments"]
    )
    assert any(
        item["content"] == "__pytest_export_moment_comment__"
        for item in data["moment_comments"]
    )
    assert any(
        item["content"] == "__pytest_export_message__" for item in data["messages"]
    )
    assert "user_id" in data["messages"][0]


def test_import_restores_new_content(tmp_path, user_client):
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.username == "__pytest_user__"))
        assert user is not None
        moment = Moment(content="__pytest_import_moment__")
        db.add(moment)
        db.flush()
        db.add(
            MomentComment(
                moment_id=moment.id,
                user_id=user.id,
                author_name=user.username,
                content="__pytest_import_moment_comment__",
                is_approved=True,
            )
        )
        db.add(
            Message(
                user_id=user.id,
                author_name=user.username,
                content="__pytest_import_message__",
            )
        )
        db.commit()

    path = tmp_path / "backup.json"
    export_content(path)

    with SessionLocal() as db:
        db.execute(delete(MomentComment))
        db.execute(delete(Moment))
        db.execute(delete(Message))
        db.commit()
        user_id = user.id

    import_content(path, replace=True)

    with SessionLocal() as db:
        moment = db.scalar(
            select(Moment).where(Moment.content == "__pytest_import_moment__")
        )
        assert moment is not None
        moment_comment = db.scalar(
            select(MomentComment).where(
                MomentComment.content == "__pytest_import_moment_comment__"
            )
        )
        assert moment_comment is not None
        assert moment_comment.user_id == user_id
        message = db.scalar(
            select(Message).where(Message.content == "__pytest_import_message__")
        )
        assert message is not None
        assert message.user_id == user_id
