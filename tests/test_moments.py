"""
========== 动态功能测试 ==========
"""

import re

from sqlalchemy import select

from app.db import SessionLocal
from app.models import Moment, MomentComment
from tests.utils import csrf_token


def _create_moment(admin_client, content: str) -> None:
    page = admin_client.get("/admin/moments/new")
    token = csrf_token(page.text)
    response = admin_client.post(
        "/admin/moments/new",
        data={"csrf_token": token, "content": content},
        follow_redirects=False,
    )
    assert response.status_code == 303


def test_admin_creates_moment_and_public_page_shows_it(client, admin_client):
    content = "__pytest_moment_public__"
    _create_moment(admin_client, content)

    page = client.get("/moments")
    assert page.status_code == 200
    assert content in page.text


def test_moment_comment_requires_approval(client, admin_client, user_client):
    moment_content = "__pytest_moment_comment__"
    _create_moment(admin_client, moment_content)

    public = user_client.get("/moments")
    token = csrf_token(public.text)
    match = re.search(r'action="[^"]*/moments/(\d+)/comments"', public.text)
    assert match is not None
    moment_id = match.group(1)

    comment = "__pytest_moment_comment_pending__"
    response = user_client.post(
        f"/moments/{moment_id}/comments",
        data={"csrf_token": token, "content": comment},
        follow_redirects=False,
    )
    assert response.status_code == 303

    assert comment not in client.get("/moments").text

    admin_page = admin_client.get("/admin/moment-comments")
    assert comment in admin_page.text
    token = csrf_token(admin_page.text)
    approve = re.search(
        r'action="[^"]*/admin/moment-comments/(\d+)/approve"',
        admin_page.text,
    )
    assert approve is not None

    response = admin_client.post(
        f"/admin/moment-comments/{approve.group(1)}/approve",
        data={"csrf_token": token},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert comment in client.get("/moments").text


def test_moment_comment_redirect_keeps_page(admin_client, user_client):
    for index in range(11):
        _create_moment(admin_client, f"__pytest_moment_page_{index}__")

    public = user_client.get("/moments?page=2")
    token = csrf_token(public.text)
    match = re.search(r'action="[^"]*/moments/(\d+)/comments"', public.text)
    assert match is not None

    response = user_client.post(
        f"/moments/{match.group(1)}/comments",
        data={
            "csrf_token": token,
            "content": "__pytest_moment_page_comment__",
            "page": "2",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert "page=2" in response.headers["location"]
    assert f"#moment-{match.group(1)}" in response.headers["location"]

    admin_page = admin_client.get("/admin/moments")
    assert "?page=2#moment-" in admin_page.text


def test_moments_caps_long_comment_threads(client, admin_client):
    content = "__pytest_moment_long_thread__"
    _create_moment(admin_client, content)

    with SessionLocal() as db:
        moment = db.scalar(select(Moment).where(Moment.content == content))
        assert moment is not None
        for index in range(25):
            db.add(
                MomentComment(
                    moment_id=moment.id,
                    author_name="tester",
                    content=f"thread comment {index}",
                    is_approved=True,
                )
            )
        db.commit()

    page = client.get("/moments")
    assert "评论（25）" in page.text
    assert "仅显示最新 20 条" in page.text
    assert "thread comment 5" in page.text
    assert "thread comment 4" not in page.text
