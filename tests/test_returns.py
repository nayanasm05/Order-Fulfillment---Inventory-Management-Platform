def test_get_return(client, auth_headers):
    response = client.get(
        "/api/returns/2",
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 2


def test_return_not_found(client, auth_headers):
    response = client.get(
        "/api/returns/999999",
        headers=auth_headers
    )

    assert response.status_code == 404


def test_invalid_return_status(client, auth_headers):
    response = client.patch(
        "/api/returns/2/status",
        headers=auth_headers,
        json={
            "status": "InvalidStatus"
        }
    )

    assert response.status_code in [400, 422]
    
