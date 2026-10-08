# Order Fulfillment & Inventory Management Platform

A secure REST API for managing products, warehouses, inventory, orders, fulfillment, returns, refunds, notifications, dashboards, and audit logs.

## Technology Stack

- Python
- FastAPI
- PostgreSQL
- SQLAlchemy
- Alembic
- Pydantic
- JWT Authentication
- Pytest
- Postman

## Core Features

### Authentication & Authorization
- User registration and login
- JWT access and refresh tokens
- Token refresh and logout
- Password change
- Role-based authorization
- Warehouse-level authorization
- Inactive users are blocked from authentication

### Product Management
- Create, list, retrieve and update products
- Product activation/deactivation
- Unique SKU validation
- Inactive products cannot be added to new orders

### Warehouse Management
- Warehouse CRUD
- Activation/deactivation
- Warehouse-level user authorization

### Inventory Management
- Inventory creation and updates
- Inventory listing with filtering, sorting and pagination
- Inventory adjustment
- Reservation and release
- Warehouse-to-warehouse transfer
- Low-stock detection
- Immutable inventory transaction records

### Order Management
- Create, list and retrieve orders
- Order item management
- Inventory reservation during order creation
- Order status workflow
- Order cancellation where permitted
- Order status history
- Idempotent order creation

### Fulfillment
- Order assignment
- Fulfillment confirmation
- Processing
- Packing
- Shipping
- Delivery
- Assignment authorization and auditing

### Returns & Refunds
- Return creation
- Return status workflow:
  `Requested -> Approved/Rejected -> Received -> Refunded`
- Refund creation and processing
- Return and refund records

### Notifications
- User notifications
- Order, inventory and workflow notifications

### Dashboards
- Admin dashboard
- Warehouse dashboard
- Customer dashboard

### Audit Logging
Important operations are recorded with user, action, entity, entity ID, timestamp, IP address and metadata.

### Idempotency
Idempotency is implemented for critical operations including:
- Create Order
- Inventory Adjustment
- Inventory Transfer

The same idempotency key prevents duplicate processing.

## Architecture

The application follows:

```text
Client
  |
  v
FastAPI Routes
  |
  v
Dependencies / Authentication / RBAC
  |
  v
Service Layer
  |
  v
Repository / Data Access Layer
  |
  v
SQLAlchemy Models
  |
  v
PostgreSQL
```

Business rules are handled in service/domain logic rather than being placed directly in route handlers.

## Project Structure

```text
Order Fulfillment & Inventory Management Platform/
|
├── app/
│   ├── core/
│   ├── repositories/
│   ├── routers/
│   ├── services/
│   ├── database.py
│   ├── dependencies.py
│   ├── models.py
│   ├── schemas.py
│   └── main.py
|
├── alembic/
│   ├── versions/
│   └── env.py
|
├── tests/
│   ├── conftest.py
│   ├── test_auth.py
│   ├── test_products.py
│   ├── test_inventory.py
│   ├── test_orders.py
│   └── test_returns.py
|
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

## Database

PostgreSQL is used as the primary database.

The database contains entities for:

```text
roles
users
products
warehouses
warehouse_users
inventory
inventory_transactions
orders
order_items
order_status_history
order_assignments
return_requests
return_items
refunds
notifications
audit_logs
refresh_tokens
idempotency_keys
```

Database schema changes are managed through Alembic migrations.

## Environment Configuration

Create a `.env` file from `.env.example`.

Example:

```env
DATABASE_URL=postgresql+psycopg2://postgres:YOUR_POSTGRES_PASSWORD@localhost:5433/order_fulfillment_db

SECRET_KEY=YOUR_SECRET_KEY_HERE
ALGORITHM=HS256

ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
```

Do not commit `.env` to source control.

## Installation

Create and activate the virtual environment:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
pip install -r requirements.txt
```

## Database Setup

Create the PostgreSQL database:

```text
order_fulfillment_db
```

Update `.env` with the PostgreSQL connection string.

Run migrations:

```powershell
python -m alembic upgrade head
```

## Run the Application

Start FastAPI with Uvicorn:

```powershell
uvicorn app.main:app --reload
```

The application runs at:

```text
http://127.0.0.1:8000
```

Swagger/OpenAPI documentation is available at:

```text
http://127.0.0.1:8000/
```

## Authentication

Login:

```http
POST /api/auth/login
```

Example request:

```json
{
  "username": "admin",
  "password": "your-password"
}
```

Use the returned access token as:

```text
Authorization: Bearer <access_token>
```

## Main API Modules

| Module | Base Path |
|---|---|
| Authentication | `/api/auth` |
| Products | `/api/products` |
| Warehouses | `/api/warehouses` |
| Inventory | `/api/inventory` |
| Orders | `/api/orders` |
| Fulfillment | `/api/orders/{order_id}/fulfillment` |
| Returns | `/api/returns` |
| Refunds | `/api/refunds` |
| Notifications | `/api/notifications` |
| Dashboard | `/api/dashboard` |
| Audit Logs | `/api/audit-logs` |

## Inventory Concurrency Strategy

Inventory operations use database transactions and row-level locking for operations that modify stock.

The application:
- Locks inventory rows before critical quantity changes
- Checks available inventory before reservation
- Prevents negative inventory
- Uses transactional inventory transfers
- Records inventory movements as transactions
- Uses unique/idempotency controls for retry-safe critical operations

This prevents concurrent requests from reserving or transferring the same stock incorrectly.

## Order Status Workflow

```text
Pending
   |
   v
Confirmed
   |
   v
Processing
   |
   v
Packed
   |
   v
Shipped
   |
   v
Delivered
```

Alternative terminal/workflow states include:

```text
Cancelled
Failed
Returned
```

Invalid state transitions are rejected by the service layer.

## Return Status Workflow

```text
Requested
   |
   +----> Rejected
   |
   v
Approved
   |
   v
Received
   |
   v
Refunded
```

Invalid return transitions are rejected.

## Idempotency

Critical requests accept an `Idempotency-Key` header.

Example:

```http
Idempotency-Key: UNIQUE-REQUEST-001
```

Retrying the same operation with the same key returns the previously stored response instead of creating a duplicate operation.

## Testing

Run the complete test suite:

```powershell
pytest -q
```

Run a specific test module:

```powershell
pytest tests/test_auth.py -v
pytest tests/test_products.py -v
pytest tests/test_inventory.py -v
pytest tests/test_orders.py -v
pytest tests/test_returns.py -v
```

The project includes tests covering authentication, authorization, products, inventory, concurrency, idempotency, orders and returns.

## Postman

Import the provided Postman collection:

```text
Order_Fulfillment_Inventory_Postman_Collection.json
```

Set:

```text
base_url = http://127.0.0.1:8000
```

Authenticate first and use the returned bearer token for protected requests.

## Documentation Deliverables

All submission documentation and supporting files should be kept in the project root under a dedicated `docs/` folder.

Recommended final structure:

```text
Order Fulfillment & Inventory Management Platform/
|
├── app/
├── alembic/
├── tests/
|
├── docs/
│   ├── Postman/
│   │   └── Order_Fulfillment_Inventory_Postman_Collection.json
│   │
│   ├── ER_Diagram/
│   │   └── Order_Fulfillment_Inventory_ER_Diagram.pdf
│   │
│   ├── Architecture_Diagram/
│   │   └── Order_Fulfillment_Inventory_Architecture_Diagram.png
│   │
│   └── API_Documentation.md
|
├── .env
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

### Submission Documentation

#### 1. Postman Collection

Location:

```text
docs/Postman/Order_Fulfillment_Inventory_Postman_Collection.json
```

Use this collection to test the REST APIs.

#### 2. ER Diagram

Location:

```text
docs/ER_Diagram/Order_Fulfillment_Inventory_ER_Diagram.pdf
```

The ER diagram represents the database entities, primary keys, foreign keys and relationships.

#### 3. Architecture Diagram

Location:

```text
docs/Architecture_Diagram/Order_Fulfillment_Inventory_Architecture_Diagram.png
```

The architecture diagram represents:

```text
Client
  ↓
FastAPI Routes
  ↓
Dependencies / Authentication / RBAC
  ↓
Services
  ↓
Repositories
  ↓
SQLAlchemy Models
  ↓
PostgreSQL
```

It also documents supporting components such as JWT authentication, notifications, audit logging, idempotency, Alembic and Pytest.

#### 4. API Documentation

Location:

```text
docs/API_Documentation.md
```

FastAPI Swagger/OpenAPI is also available from the application root.

#### 5. Configuration Files

```text
.env.example
.gitignore
```

`.env.example` is safe to commit. The real `.env` file must not be committed.


## Security Notes

- Passwords are stored using secure password hashing.
- JWT access tokens are used for protected APIs.
- Refresh tokens are persisted and can be revoked.
- Role and warehouse authorization are enforced.
- `.env` must not be committed.
- Audit records are intended to remain immutable to normal application users.

## Error Handling

The API handles common HTTP errors including:

```text
400 Bad Request
401 Unauthorized
403 Forbidden
404 Not Found
409 Conflict
422 Validation Error
500 Internal Server Error
```

Business validation includes cases such as insufficient inventory, invalid order status transitions, invalid return transitions, inactive products, warehouse access violations and duplicate/idempotent requests.

## Development

Recommended workflow:

```powershell
.venv\Scripts\Activate.ps1
python -m alembic upgrade head
uvicorn app.main:app --reload
```

For testing:

```powershell
pytest -q
```

## License

This project was developed as a backend engineering assignment demonstrating production-oriented API design, database transactions, authorization, concurrency handling, inventory management, order processing and automated testing.
