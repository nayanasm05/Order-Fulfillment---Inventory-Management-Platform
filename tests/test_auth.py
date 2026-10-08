def test_admin_login(client):
    response = client.post(
        "/api/auth/login",
        json={
            "username": "admin",
            "password": "Admin@12345"
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_invalid_login(client):
    response = client.post(
        "/api/auth/login",
        json={
            "username": "admin",
            "password": "WrongPassword123"
        }
    )

    assert response.status_code in [401, 403]