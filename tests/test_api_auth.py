from tests.conftest import USER_NICKNAME


def test_auth_me_anonymous(client):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 200
    assert response.json() == {"user": None}


def test_auth_me_logged_in(user_client):
    response = user_client.get("/api/v1/auth/me")
    assert response.status_code == 200
    assert response.json() == {"user": {"name": USER_NICKNAME}}
