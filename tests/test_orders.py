def test_list_orders(client, auth_headers):
    response = client.get(
        "/api/orders",
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "pagination" in data


def test_get_order(client, auth_headers):
    response = client.get(
        "/api/orders/1",
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 1


def test_order_not_found(client, auth_headers):
    response = client.get(
        "/api/orders/999999",
        headers=auth_headers
    )

    assert response.status_code == 404


def test_order_requires_authentication(client):
    response = client.get("/api/orders")

    assert response.status_code in [401, 403]


def test_create_order_idempotency(client, auth_headers):
    payload = {
        "warehouse_id": 1,
        "items": [
            {
                "product_id": 1,
                "quantity": 1
            }
        ],
        "discount": 0,
        "tax": 0
    }

    headers = {
        **auth_headers,
        "Idempotency-Key": "PYTEST-ORDER-IDEMPOTENCY-001"
    }

    first_response = client.post(
        "/api/orders",
        json=payload,
        headers=headers
    )

    assert first_response.status_code == 201

    first_order = first_response.json()

    second_response = client.post(
        "/api/orders",
        json=payload,
        headers=headers
    )

    assert second_response.status_code == 201

    second_order = second_response.json()

    assert second_order["id"] == first_order["id"]
    assert second_order["order_number"] == first_order["order_number"]


def test_invalid_order_status_transition(client, auth_headers):
    response = client.patch(
        "/api/orders/1/status",
        headers=auth_headers,
        json={
            "status": "Processing",
            "reason": "Pytest invalid transition test"
        }
    )

    assert response.status_code == 400
    assert "Invalid order status transition" in response.json()["detail"]
    
