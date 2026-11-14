"""主题偏好读取测试。"""


def test_admin_login_reads_theme_cookie(client):
    response = client.get("/admin/login")
    assert response.status_code == 200
    assert "theme-v2" in response.text
