"""
========== HTMX 渐进增强测试 ==========
"""

from datetime import date

from sqlalchemy import delete, select

from app.db import SessionLocal
from app.models import BlogPost, Comment, Moment, MomentComment
from tests.utils import csrf_token

AUTHOR = "__pytest_user__"
BODY = "unique pytest htmx body"
HTMX = {"HX-Request": "true"}


def _cleanup_comments() -> None:
    with SessionLocal() as db:
        db.execute(delete(Comment).where(Comment.author_name == AUTHOR))
        db.commit()


def test_htmx_asset(client):
    response = client.get("/static/js/vendor/htmx.min.js")
    assert response.status_code == 200
    assert "htmx" in response.text
    assert "htmx.min.js" in client.get("/").text


def test_pagination_uses_htmx_boost(client):
    with SessionLocal() as db:
        for index in range(6):
            db.add(
                BlogPost(
                    title=f"__pytest_htmx_page_{index}",
                    slug=f"__pytest-htmx-page-{index}",
                    summary="",
                    content="content",
                    published_at=date(2020, 1, index + 1),
                    tags=[],
                )
            )
        db.commit()

    try:
        page = client.get("/posts")
        assert 'hx-boost="true"' in page.text
    finally:
        with SessionLocal() as db:
            db.execute(
                delete(BlogPost).where(BlogPost.title.like("__pytest_htmx_page_%"))
            )
            db.commit()


def test_comment_htmx_partial(user_client):
    _cleanup_comments()
    try:
        token = csrf_token(user_client.get("/posts/1").text)
        response = user_client.post(
            "/posts/1/comments",
            data={"csrf_token": token, "content": BODY},
            headers=HTMX,
            follow_redirects=False,
        )
        assert response.status_code == 200
        assert 'id="comments"' in response.text
        assert "评论已提交" in response.text
        assert "<html" not in response.text

        with SessionLocal() as db:
            assert (
                db.scalar(select(Comment).where(Comment.author_name == AUTHOR))
                is not None
            )
    finally:
        _cleanup_comments()


def test_comment_htmx_requires_login(client):
    token = csrf_token(client.get("/login").text)
    response = client.post(
        "/posts/1/comments",
        data={"csrf_token": token, "content": BODY},
        headers=HTMX,
        follow_redirects=False,
    )
    assert response.status_code == 200
    assert response.headers["hx-redirect"].startswith("/login")


def test_guestbook_htmx_partial(user_client):
    token = csrf_token(user_client.get("/guestbook").text)
    response = user_client.post(
        "/guestbook",
        data={"csrf_token": token, "content": BODY},
        headers=HTMX,
        follow_redirects=False,
    )
    assert response.status_code == 200
    assert 'id="guestbook-panel"' in response.text
    assert "留言已提交" in response.text
    assert "<html" not in response.text


def test_moment_comment_htmx_partial(user_client):
    with SessionLocal() as db:
        moment = Moment(content="__pytest_htmx_moment__")
        db.add(moment)
        db.commit()
        moment_id = moment.id

    token = csrf_token(user_client.get("/moments").text)
    response = user_client.post(
        f"/moments/{moment_id}/comments",
        data={"csrf_token": token, "content": BODY, "page": "1"},
        headers=HTMX,
        follow_redirects=False,
    )
    assert response.status_code == 200
    assert f'id="moment-comments-{moment_id}"' in response.text
    assert "评论已提交" in response.text
    assert "<html" not in response.text


def test_admin_comment_approve_htmx(admin_client):
    with SessionLocal() as db:
        comment = Comment(
            post_id=1,
            author_name="__pytest_htmx_admin__",
            content=BODY,
            is_approved=False,
        )
        db.add(comment)
        db.commit()
        comment_id = comment.id

    try:
        token = csrf_token(admin_client.get("/admin/comments").text)
        response = admin_client.post(
            f"/admin/comments/{comment_id}/approve",
            data={"csrf_token": token},
            headers=HTMX,
            follow_redirects=False,
        )
        assert response.status_code == 200
        assert response.text.strip().startswith("<tr>")
        assert "已通过" in response.text

        with SessionLocal() as db:
            assert db.get(Comment, comment_id).is_approved is True
    finally:
        with SessionLocal() as db:
            db.execute(delete(Comment).where(Comment.id == comment_id))
            db.commit()


def test_admin_moment_comment_approve_htmx(admin_client):
    with SessionLocal() as db:
        moment = Moment(content="__pytest_htmx_admin_moment__")
        db.add(moment)
        db.flush()
        comment = MomentComment(
            moment_id=moment.id,
            author_name="__pytest_htmx_admin__",
            content=BODY,
            is_approved=False,
        )
        db.add(comment)
        db.commit()
        comment_id = comment.id

    try:
        token = csrf_token(admin_client.get("/admin/moment-comments").text)
        response = admin_client.post(
            f"/admin/moment-comments/{comment_id}/approve",
            data={"csrf_token": token, "page": "1"},
            headers=HTMX,
            follow_redirects=False,
        )
        assert response.status_code == 200
        assert response.text.strip().startswith("<tr>")
        assert "已通过" in response.text

        with SessionLocal() as db:
            assert db.get(MomentComment, comment_id).is_approved is True
    finally:
        with SessionLocal() as db:
            db.execute(delete(MomentComment).where(MomentComment.id == comment_id))
            db.execute(
                delete(Moment).where(Moment.content == "__pytest_htmx_admin_moment__")
            )
            db.commit()
