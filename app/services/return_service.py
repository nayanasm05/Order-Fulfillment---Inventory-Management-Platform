from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import (
    Inventory,
    InventoryTransaction,
    Order,
    OrderItem,
    ReturnRequest,
    User,
    WarehouseUser,
)
from app.repositories.return_repository import (
    create_return,
    get_existing_return_quantity,
    get_return_by_id,
    get_returns_for_customer,
    get_returns_for_order,
)
from app.services.audit_service import record_audit
from app.services.notification_helper import (
    notify_return_approved,
    notify_return_requested,
)


VALID_RETURN_STATUSES = {
    "Requested",
    "Approved",
    "Rejected",
    "Received",
    "Refunded",
}


def get_order_item(db: Session, order_item_id: int):
    item = (
        db.query(OrderItem)
        .filter(OrderItem.id == order_item_id)
        .first()
    )

    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order item not found",
        )

    return item


def check_warehouse_access(
    db: Session,
    user: User,
    warehouse_id: int,
):
    role_name = user.role.name.lower() if user.role else ""

    if role_name == "admin":
        return

    access = (
        db.query(WarehouseUser)
        .filter(
            WarehouseUser.user_id == user.id,
            WarehouseUser.warehouse_id == warehouse_id,
        )
        .first()
    )

    if access is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to access this warehouse",
        )


def create_return_request(
    db: Session,
    order_item_id: int,
    quantity: int,
    reason: str,
    current_user: User,
):
    item = get_order_item(db, order_item_id)

    order = (
        db.query(Order)
        .filter(Order.id == item.order_id)
        .first()
    )

    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    if order.status != "Delivered":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Returns can only be requested for delivered orders",
        )

    role_name = current_user.role.name.lower() if current_user.role else ""

    if role_name == "customer":
        if order.customer_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to return this order",
            )
    else:
        check_warehouse_access(
            db,
            current_user,
            order.warehouse_id,
        )

    if quantity > item.quantity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Return quantity cannot exceed ordered quantity",
        )

    existing_quantity = get_existing_return_quantity(
        db,
        order_item_id,
    )

    if existing_quantity + quantity > item.quantity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Requested return quantity exceeds remaining quantity",
        )

    return_request = ReturnRequest(
        order_id=order.id,
        order_item_id=item.id,
        customer_id=order.customer_id,
        quantity=quantity,
        reason=reason,
        status="Requested",
    )

    create_return(db, return_request)

    db.commit()
    db.refresh(return_request)

    try:
        record_audit(
            db=db,
            user_id=current_user.id,
            action="RETURN_CREATED",
            entity_type="ReturnRequest",
            entity_id=return_request.id,
            metadata_json={
                "order_id": return_request.order_id,
                "order_item_id": return_request.order_item_id,
                "customer_id": return_request.customer_id,
                "quantity": return_request.quantity,
                "status": "Requested",
                "reason": reason,
            },
        )
    except Exception:
        pass

    try:
        notify_return_requested(
            db=db,
            user_id=return_request.customer_id,
            return_id=return_request.id,
            order_id=return_request.order_id,
        )
    except Exception:
        pass

    return return_request


def update_return_status(
    db: Session,
    return_id: int,
    new_status: str,
    current_user: User,
):
    return_request = get_return_by_id(db, return_id)

    if return_request is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Return request not found",
        )

    if new_status not in VALID_RETURN_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid return status",
        )

    order = (
        db.query(Order)
        .filter(Order.id == return_request.order_id)
        .first()
    )

    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    role_name = current_user.role.name.lower() if current_user.role else ""

    if role_name not in ["admin", "warehouse manager"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Admin or Warehouse Manager can update returns",
        )

    check_warehouse_access(
        db,
        current_user,
        order.warehouse_id,
    )

    old_status = return_request.status

    allowed_transitions = {
        "Requested": {"Approved", "Rejected"},
        "Approved": {"Received"},
        "Received": {"Refunded"},
        "Rejected": set(),
        "Refunded": set(),
    }

    if new_status == old_status:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Return is already in this status",
        )

    if new_status not in allowed_transitions.get(old_status, set()):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid return status transition from {old_status} to {new_status}",
        )

    if new_status == "Received":
        order_item = (
            db.query(OrderItem)
            .filter(OrderItem.id == return_request.order_item_id)
            .first()
        )

        if order_item is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order item not found",
            )

        inventory = (
            db.query(Inventory)
            .filter(
                Inventory.product_id == order_item.product_id,
                Inventory.warehouse_id == order.warehouse_id,
            )
            .with_for_update()
            .first()
        )

        if inventory is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Inventory record not found",
            )

        inventory.quantity += return_request.quantity

        transaction = InventoryTransaction(
            product_id=inventory.product_id,
            warehouse_id=inventory.warehouse_id,
            transaction_type="RETURN",
            quantity=return_request.quantity,
            reference_id=str(return_request.id),
            user_id=current_user.id,
            reason="Returned order item",
        )

        db.add(transaction)

        return_request.processed_by = current_user.id
        return_request.processed_at = datetime.utcnow()

    return_request.status = new_status

    db.commit()
    db.refresh(return_request)

    try:
        record_audit(
            db=db,
            user_id=current_user.id,
            action=f"RETURN_{new_status.upper()}",
            entity_type="ReturnRequest",
            entity_id=return_request.id,
            metadata_json={
                "order_id": return_request.order_id,
                "customer_id": return_request.customer_id,
                "order_item_id": return_request.order_item_id,
                "quantity": return_request.quantity,
                "old_status": old_status,
                "new_status": new_status,
            },
        )
    except Exception:
        pass

    try:
        if new_status == "Approved":
            notify_return_approved(
                db=db,
                user_id=return_request.customer_id,
                return_id=return_request.id,
                order_id=return_request.order_id,
            )
    except Exception:
        pass

    return return_request


def get_return(
    db: Session,
    return_id: int,
    current_user: User,
):
    return_request = get_return_by_id(db, return_id)

    if return_request is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Return request not found",
        )

    order = (
        db.query(Order)
        .filter(Order.id == return_request.order_id)
        .first()
    )

    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    role_name = current_user.role.name.lower() if current_user.role else ""

    if role_name == "customer":
        if return_request.customer_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to view this return",
            )
    else:
        check_warehouse_access(
            db,
            current_user,
            order.warehouse_id,
        )

    return return_request


def list_order_returns(
    db: Session,
    order_id: int,
    current_user: User,
):
    order = (
        db.query(Order)
        .filter(Order.id == order_id)
        .first()
    )

    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    role_name = current_user.role.name.lower() if current_user.role else ""

    if role_name == "customer":
        if order.customer_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to view these returns",
            )
    else:
        check_warehouse_access(
            db,
            current_user,
            order.warehouse_id,
        )

    return get_returns_for_order(db, order_id)


def list_customer_returns(
    db: Session,
    current_user: User,
):
    return get_returns_for_customer(
        db,
        current_user.id,
    )