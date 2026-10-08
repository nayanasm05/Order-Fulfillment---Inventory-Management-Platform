from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserRegister(BaseModel):
    username: str = Field(min_length=3, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    role_id: int


class UserLogin(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class UserResponse(BaseModel):
    id: int
    username: str
    email: EmailStr
    role_id: int
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class ProductCreate(BaseModel):
    sku: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    category: str | None = Field(default=None, max_length=100)
    price: float = Field(gt=0)


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    category: str | None = Field(default=None, max_length=100)
    price: float | None = Field(default=None, gt=0)
    is_active: bool | None = None


class ProductResponse(BaseModel):
    id: int
    sku: str
    name: str
    description: str | None
    category: str | None
    price: float
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class WarehouseCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    code: str = Field(min_length=1, max_length=50)
    location: str | None = Field(default=None, max_length=255)


class WarehouseUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    location: str | None = Field(default=None, max_length=255)
    is_active: bool | None = None


class WarehouseResponse(BaseModel):
    id: int
    name: str
    code: str
    location: str | None
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class InventoryCreate(BaseModel):
    product_id: int
    warehouse_id: int
    quantity: int = Field(default=0, ge=0)
    reorder_level: int = Field(default=0, ge=0)


class InventoryUpdate(BaseModel):
    quantity: int | None = Field(default=None, ge=0)
    reserved_quantity: int | None = Field(default=None, ge=0)
    reorder_level: int | None = Field(default=None, ge=0)


class InventoryResponse(BaseModel):
    id: int
    product_id: int
    warehouse_id: int
    quantity: int
    reserved_quantity: int
    reorder_level: int

    model_config = ConfigDict(from_attributes=True)


class InventoryAdjustmentRequest(BaseModel):
    inventory_id: int
    quantity: int
    reason: str = Field(min_length=1, max_length=500)


class InventoryTransactionResponse(BaseModel):
    id: int
    product_id: int
    warehouse_id: int
    transaction_type: str
    quantity: int
    reference_id: str | None
    user_id: int
    reason: str | None
    metadata_json: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InventoryTransferRequest(BaseModel):
    product_id: int
    from_warehouse_id: int
    to_warehouse_id: int
    quantity: int = Field(gt=0)
    reason: str = Field(min_length=1, max_length=500)


class InventoryReservationRequest(BaseModel):
    inventory_id: int
    quantity: int = Field(gt=0)
    reference_id: str | None = Field(default=None, max_length=100)


class InventoryReleaseRequest(BaseModel):
    inventory_id: int
    quantity: int = Field(gt=0)
    reference_id: str | None = Field(default=None, max_length=100)


class OrderItemCreate(BaseModel):
    product_id: int = Field(gt=0)
    quantity: int = Field(gt=0)


class OrderCreate(BaseModel):
    warehouse_id: int = Field(gt=0)
    items: list[OrderItemCreate] = Field(min_length=1)
    discount: Decimal = Field(default=Decimal("0.00"), ge=0)
    tax: Decimal = Field(default=Decimal("0.00"), ge=0)
    expected_delivery: datetime | None = None


class OrderItemResponse(BaseModel):
    id: int
    order_id: int
    product_id: int
    quantity: int
    unit_price: Decimal
    discount: Decimal
    tax: Decimal
    total_amount: Decimal
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OrderStatusHistoryResponse(BaseModel):
    id: int
    order_id: int
    old_status: str | None
    new_status: str
    changed_by: int
    reason: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OrderResponse(BaseModel):
    id: int
    order_number: str
    customer_id: int
    warehouse_id: int
    subtotal: Decimal
    discount: Decimal
    tax: Decimal
    total_amount: Decimal
    status: str
    payment_status: str
    expected_delivery: datetime | None
    created_at: datetime
    updated_at: datetime
    items: list[OrderItemResponse] = []
    status_history: list[OrderStatusHistoryResponse] = []

    model_config = ConfigDict(from_attributes=True)


class OrderStatusUpdate(BaseModel):
    status: str = Field(min_length=1, max_length=50)
    reason: str | None = Field(default=None, max_length=500)


class OrderCancellationRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=500)


class OrderListResponse(BaseModel):
    id: int
    order_number: str
    customer_id: int
    warehouse_id: int
    total_amount: Decimal
    status: str
    payment_status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OrderAssignmentCreate(BaseModel):
    order_id: int = Field(gt=0)
    assigned_to: int = Field(gt=0)
    reason: str | None = Field(default=None, max_length=500)


class OrderAssignmentResponse(BaseModel):
    id: int
    order_id: int
    assigned_to: int
    assigned_by: int
    assigned_at: datetime
    is_active: bool
    reason: str | None

    model_config = ConfigDict(from_attributes=True)


class OrderReassignmentRequest(BaseModel):
    assigned_to: int = Field(gt=0)
    reason: str | None = Field(default=None, max_length=500)
    

class ReturnRequestCreate(BaseModel):
    order_item_id: int = Field(gt=0)
    quantity: int = Field(gt=0)
    reason: str = Field(min_length=3, max_length=500)


class ReturnStatusUpdate(BaseModel):
    status: str
    reason: str | None = Field(default=None, max_length=500)


class ReturnRequestResponse(BaseModel):
    id: int
    order_id: int
    order_item_id: int
    customer_id: int
    quantity: int
    reason: str
    status: str
    processed_by: int | None
    processed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
    
class RefundProcessRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=500)


class RefundResponse(BaseModel):
    id: int
    return_request_id: int
    order_id: int
    customer_id: int
    amount: float
    status: str
    processed_by: int | None
    processed_at: datetime | None
    reason: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
    
class NotificationCreate(BaseModel):
    user_id: int = Field(gt=0)
    title: str = Field(min_length=1, max_length=200)
    message: str = Field(min_length=1, max_length=1000)
    notification_type: str = Field(min_length=1, max_length=50)
    reference_type: str | None = Field(default=None, max_length=50)
    reference_id: int | None = Field(default=None, gt=0)


class NotificationResponse(BaseModel):
    id: int
    user_id: int
    title: str
    message: str
    notification_type: str
    reference_type: str | None
    reference_id: int | None
    is_read: bool
    created_at: datetime
    read_at: datetime | None

    model_config = ConfigDict(from_attributes=True)
    
class PaginationResponse(BaseModel):
    page: int
    page_size: int
    total: int
    total_pages: int


class OrderListPaginatedResponse(BaseModel):
    items: list[OrderResponse]
    pagination: PaginationResponse


class InventoryListPaginatedResponse(BaseModel):
    items: list[InventoryResponse]
    pagination: PaginationResponse
    
class AuditLogResponse(BaseModel):
    id: int
    user_id: int | None
    action: str
    entity_type: str
    entity_id: int | None
    ip_address: str | None
    metadata_json: dict | None
    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True
    )


class AuditLogListResponse(BaseModel):
    items: list[AuditLogResponse]
    page: int
    page_size: int
    total: int
    total_pages: int