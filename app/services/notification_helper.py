from sqlalchemy.orm import Session

from app.services.notification_service import create_user_notification


def notify_user(
    db: Session,
    user_id: int,
    title: str,
    message: str,
    notification_type: str,
    reference_type: str | None = None,
    reference_id: int | None = None,
):
    return create_user_notification(
        db=db,
        user_id=user_id,
        title=title,
        message=message,
        notification_type=notification_type,
        reference_type=reference_type,
        reference_id=reference_id,
    )


def notify_order_created(
    db: Session,
    user_id: int,
    order_id: int,
    order_number: str,
):
    return notify_user(
        db=db,
        user_id=user_id,
        title="Order Created",
        message=f"Order {order_number} has been created successfully.",
        notification_type="order_created",
        reference_type="order",
        reference_id=order_id,
    )


def notify_order_confirmed(
    db: Session,
    user_id: int,
    order_id: int,
    order_number: str,
):
    return notify_user(
        db=db,
        user_id=user_id,
        title="Order Confirmed",
        message=f"Order {order_number} has been confirmed.",
        notification_type="order_confirmed",
        reference_type="order",
        reference_id=order_id,
    )


def notify_order_assigned(
    db: Session,
    user_id: int,
    order_id: int,
    order_number: str,
):
    return notify_user(
        db=db,
        user_id=user_id,
        title="Order Assigned",
        message=f"Order {order_number} has been assigned to you.",
        notification_type="order_assigned",
        reference_type="order",
        reference_id=order_id,
    )


def notify_order_shipped(
    db: Session,
    user_id: int,
    order_id: int,
    order_number: str,
):
    return notify_user(
        db=db,
        user_id=user_id,
        title="Order Shipped",
        message=f"Order {order_number} has been shipped.",
        notification_type="order_shipped",
        reference_type="order",
        reference_id=order_id,
    )


def notify_order_delivered(
    db: Session,
    user_id: int,
    order_id: int,
    order_number: str,
):
    return notify_user(
        db=db,
        user_id=user_id,
        title="Order Delivered",
        message=f"Order {order_number} has been delivered.",
        notification_type="order_delivered",
        reference_type="order",
        reference_id=order_id,
    )


def notify_order_cancelled(
    db: Session,
    user_id: int,
    order_id: int,
    order_number: str,
):
    return notify_user(
        db=db,
        user_id=user_id,
        title="Order Cancelled",
        message=f"Order {order_number} has been cancelled.",
        notification_type="order_cancelled",
        reference_type="order",
        reference_id=order_id,
    )


def notify_return_requested(
    db: Session,
    user_id: int,
    return_id: int,
    order_id: int,
):
    return notify_user(
        db=db,
        user_id=user_id,
        title="Return Requested",
        message=f"A return request has been created for order {order_id}.",
        notification_type="return_requested",
        reference_type="return",
        reference_id=return_id,
    )


def notify_return_approved(
    db: Session,
    user_id: int,
    return_id: int,
    order_id: int,
):
    return notify_user(
        db=db,
        user_id=user_id,
        title="Return Approved",
        message=f"Your return request for order {order_id} has been approved.",
        notification_type="return_approved",
        reference_type="return",
        reference_id=return_id,
    )


def notify_low_stock(
    db: Session,
    user_id: int,
    inventory_id: int,
    product_id: int,
    warehouse_id: int,
    available_quantity: int,
):
    return notify_user(
        db=db,
        user_id=user_id,
        title="Low Stock Alert",
        message=(
            f"Product {product_id} has low stock in warehouse "
            f"{warehouse_id}. Available quantity: {available_quantity}."
        ),
        notification_type="low_stock",
        reference_type="inventory",
        reference_id=inventory_id,
    )


def notify_inventory_transfer(
    db: Session,
    user_id: int,
    product_id: int,
    from_warehouse_id: int,
    to_warehouse_id: int,
    quantity: int,
):
    return notify_user(
        db=db,
        user_id=user_id,
        title="Inventory Transfer",
        message=(
            f"{quantity} units of product {product_id} were transferred "
            f"from warehouse {from_warehouse_id} to warehouse "
            f"{to_warehouse_id}."
        ),
        notification_type="inventory_transfer",
        reference_type="inventory",
        reference_id=product_id,
    )


def notify_failed_order_processing(
    db: Session,
    user_id: int,
    order_id: int,
    order_number: str,
    reason: str,
):
    return notify_user(
        db=db,
        user_id=user_id,
        title="Order Processing Failed",
        message=(
            f"Processing of order {order_number} failed. "
            f"Reason: {reason}"
        ),
        notification_type="order_processing_failed",
        reference_type="order",
        reference_id=order_id,
    )