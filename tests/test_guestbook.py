"""
========== 留言功能测试 ==========
"""

from tests.utils import csrf_token


def test_guestbook_requires_login(client):
    page = client.get("/guestbook")
    assert page.status_code == 200
    assert "后才能留言" in page.text
    assert "提交留言" not in page.text

    login_page = client.get("/login")
    token = csrf_token(login_page.text)
    response = client.post(
        "/guestbook",
        data={
            "csrf_token": token,
            "content": "__pytest_guestbook_anon__",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert "/login" in response.headers["location"]


def test_logged_in_user_leaves_message(client, user_client):
    content = "__pytest_guestbook_message__"
    page = user_client.get("/guestbook")
    token = csrf_token(page.text)
    response = user_client.post(
        "/guestbook",
        data={"csrf_token": token, "content": content},
        follow_redirects=False,
    )
    assert response.status_code == 303

    public = client.get("/guestbook")
    assert content in public.text
