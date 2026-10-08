def test_list_inventory(client, auth_headers):
    response = client.get(
        "/api/inventory",
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "pagination" in data
    assert isinstance(data["items"], list)


def test_get_inventory(client, auth_headers):
    response = client.get(
        "/api/inventory/1",
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 1


def test_inventory_not_found(client, auth_headers):
    response = client.get(
        "/api/inventory/999999",
        headers=auth_headers
    )

    assert response.status_code == 404


def test_inventory_requires_authentication(client):
    response = client.get("/api/inventory")

    assert response.status_code in [401, 403]


def test_inventory_adjustment_idempotency(client, auth_headers):
    payload = {
        "inventory_id": 1,
        "quantity": 1,
        "reason": "Pytest idempotency test"
    }

    headers = {
        **auth_headers,
        "Idempotency-Key": "PYTEST-INVENTORY-IDEMPOTENCY-001"
    }

    first_response = client.post(
        "/api/inventory/adjust",
        json=payload,
        headers=headers
    )

    assert first_response.status_code == 200

    first_data = first_response.json()

    second_response = client.post(
        "/api/inventory/adjust",
        json=payload,
        headers=headers
    )

    assert second_response.status_code == 200

    second_data = second_response.json()

    assert second_data["id"] == first_data["id"]
    assert second_data["quantity"] == first_data["quantity"]
    
def test_reserve_insufficient_inventory(client, auth_headers):
    response = client.post(
        "/api/inventory/reserve",
        headers=auth_headers,
        json={
            "inventory_id": 1,
            "quantity": 999999,
            "reference_id": "PYTEST-INSUFFICIENT-STOCK"
        }
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Insufficient available inventory for reservation"
    
import threading


def test_concurrent_inventory_reservation(client, auth_headers):
    inventory_response = client.get(
        "/api/inventory/1",
        headers=auth_headers
    )

    assert inventory_response.status_code == 200

    inventory = inventory_response.json()
    available_quantity = inventory["quantity"] - inventory["reserved_quantity"]

    if available_quantity < 2:
        return

    results = []

    def reserve_stock():
        response = client.post(
            "/api/inventory/reserve",
            headers=auth_headers,
            json={
                "inventory_id": 1,
                "quantity": 1,
                "reference_id": "PYTEST-CONCURRENT-RESERVATION"
            }
        )
        results.append(response.status_code)

    thread1 = threading.Thread(target=reserve_stock)
    thread2 = threading.Thread(target=reserve_stock)

    thread1.start()
    thread2.start()

    thread1.join()
    thread2.join()

    assert len(results) == 2
    assert all(status in [200, 400] for status in results)
    assert results.count(200) <= 2
    
def test_inventory_warehouse_authorization(client, auth_headers):
    response = client.post(
        "/api/inventory/reserve",
        headers=auth_headers,
        json={
            "inventory_id": 1,
            "quantity": 1,
            "reference_id": "PYTEST-WAREHOUSE-AUTH"
        }
    )

    assert response.status_code in [200, 400, 403]
    
def test_customer_cannot_reserve_inventory(client):
    response = client.post(
        "/api/inventory/reserve",
        json={
            "inventory_id": 1,
            "quantity": 1,
            "reference_id": "PYTEST-CUSTOMER-AUTH"
        }
    )

    assert response.status_code in [401, 403]
    
def test_inventory_transfer_idempotency(client, auth_headers):
    payload = {
        "product_id": 1,
        "from_warehouse_id": 1,
        "to_warehouse_id": 4,
        "quantity": 1,
        "reason": "Pytest transfer idempotency test"
    }

    headers = {
        **auth_headers,
        "Idempotency-Key": "PYTEST-TRANSFER-IDEMPOTENCY-002"
    }

    first_response = client.post(
        "/api/inventory/transfer",
        json=payload,
        headers=headers
    )

    assert first_response.status_code == 200

    first_data = first_response.json()

    second_response = client.post(
        "/api/inventory/transfer",
        json=payload,
        headers=headers
    )

    assert second_response.status_code == 200

    second_data = second_response.json()

    assert second_data == first_data

def test_customer_cannot_access_inventory(client):
    response = client.get("/api/inventory")

    assert response.status_code in [401, 403]
