def test_list_products(client, auth_headers):
    response = client.get(
        "/api/products",
        headers=auth_headers
    )

    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_product(client, auth_headers):
    response = client.get(
        "/api/products/1",
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 1


def test_product_not_found(client, auth_headers):
    response = client.get(
        "/api/products/999999",
        headers=auth_headers
    )

    assert response.status_code == 404


def test_products_requires_authentication(client):
    response = client.get("/api/products")

    assert response.status_code in [401, 403]