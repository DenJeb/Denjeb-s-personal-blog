"""
========== 用户注销时删除全部关联记录 ==========
"""

import re

from tests.utils import csrf_token

USER_PASSWORD = "UserPass123!"


def _create_moment(admin_client, content: str) -> None:
    page = admin_client.get("/admin/moments/new")
    token = csrf_token(page.text)
    response = admin_client.post(
        "/admin/moments/new",
        data={"csrf_token": token, "content": content},
        follow_redirects=False,
    )
    assert response.status_code == 303


def test_account_deletion_removes_all_user_records(client, admin_client, user_client):
    _create_moment(admin_client, "__pytest_cascade_moment__")

    blog_comment = "__pytest_cascade_blog_comment__"
    post_page = user_client.get("/posts/1")
    token = csrf_token(post_page.text)
    response = user_client.post(
        "/posts/1/comments",
        data={"csrf_token": token, "content": blog_comment},
        follow_redirects=False,
    )
    assert response.status_code == 303

    moment_comment = "__pytest_cascade_moment_comment__"
    moments_page = user_client.get("/moments")
    token = csrf_token(moments_page.text)
    match = re.search(r'action="[^"]*/moments/(\d+)/comments"', moments_page.text)
    assert match is not None
    response = user_client.post(
        f"/moments/{match.group(1)}/comments",
        data={"csrf_token": token, "content": moment_comment},
        follow_redirects=False,
    )
    assert response.status_code == 303

    message_content = "__pytest_cascade_message__"
    guestbook_page = user_client.get("/guestbook")
    token = csrf_token(guestbook_page.text)
    response = user_client.post(
        "/guestbook",
        data={"csrf_token": token, "content": message_content},
        follow_redirects=False,
    )
    assert response.status_code == 303

    assert blog_comment in admin_client.get("/admin/comments").text
    assert moment_comment in admin_client.get("/admin/moment-comments").text
    assert message_content in admin_client.get("/admin/messages").text

    delete_page = user_client.get("/account/delete")
    token = csrf_token(delete_page.text)
    response = user_client.post(
        "/account/delete",
        data={"csrf_token": token, "password": USER_PASSWORD},
        follow_redirects=False,
    )
    assert response.status_code == 303

    assert blog_comment not in admin_client.get("/admin/comments").text
    assert moment_comment not in admin_client.get("/admin/moment-comments").text
    assert message_content not in admin_client.get("/admin/messages").text
