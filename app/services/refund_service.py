from datetime import datetime
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import (
    Order,
    OrderItem,
    ReturnRequest,
    User,
    WarehouseUser,
    Refund,
)
from app.repositories.refund_repository import (
    create_refund,
    get_customer_refunds,
    get_refund_by_id,
    get_refund_by_return_id,
)
from app.services.audit_service import record_audit

VALID_REFUND_STATUSES = {"Pending", "Processed", "Failed"}

def check_warehouse_access(
    db: Session,
    user: User,
    warehouse_id: int,
):
    if user.role.name == "Admin":
        return True

    assignment = (
        db.query(WarehouseUser)
        .filter(
            WarehouseUser.user_id == user.id,
            WarehouseUser.warehouse_id == warehouse_id,
            WarehouseUser.is_active.is_(True),
        )
        .first()
    )

    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this warehouse",
        )

    return True

def calculate_refund_amount(
    order_item: OrderItem,
    quantity: int,
):
    return Decimal(str(order_item.unit_price)) * Decimal(quantity)

def create_refund_for_return(
    db: Session,
    return_request_id: int,
    current_user: User,
    reason: str | None = None,
):
    return_request = (
        db.query(ReturnRequest)
        .filter(ReturnRequest.id == return_request_id)
        .first()
    )

    if not return_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Return request not found",
        )

    if return_request.status != "Processed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Refund can only be created for a processed return",
        )

    existing_refund = get_refund_by_return_id(
        db,
        return_request_id,
    )

    if existing_refund:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Refund already exists for this return",
        )

    order = (
        db.query(Order)
        .filter(Order.id == return_request.order_id)
        .first()
    )

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    if current_user.id == return_request.customer_id:
        pass
    elif current_user.role.name == "Admin":
        pass
    else:
        check_warehouse_access(
            db,
            current_user,
            order.warehouse_id,
        )

    order_item = (
        db.query(OrderItem)
        .filter(OrderItem.id == return_request.order_item_id)
        .first()
    )

    if not order_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order item not found",
        )

    amount = calculate_refund_amount(
        order_item,
        return_request.quantity,
    )

    refund = Refund(
        return_request_id=return_request.id,
        order_id=return_request.order_id,
        customer_id=return_request.customer_id,
        amount=amount,
        status="Pending",
        reason=reason,
    )

    create_refund(db, refund)

    db.commit()
    db.refresh(refund)

    try:
        record_audit(
            db=db,
            user_id=current_user.id,
            action="REFUND_CREATED",
            entity_type="Refund",
            entity_id=refund.id,
            metadata_json={
                "return_request_id": return_request.id,
                "order_id": return_request.order_id,
                "customer_id": return_request.customer_id,
                "amount": str(amount),
                "status": "Pending",
            },
        )
    except Exception:
        pass

    return refund

def process_refund(
    db: Session,
    refund_id: int,
    current_user: User,
    reason: str | None = None,
):
    refund = get_refund_by_id(db, refund_id)

    if not refund:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Refund not found",
        )

    if refund.status != "Pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only pending refunds can be processed",
        )

    order = (
        db.query(Order)
        .filter(Order.id == refund.order_id)
        .first()
    )

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    if current_user.role.name not in {
        "Admin",
        "Warehouse Manager",
    }:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Admin or Warehouse Manager can process refunds",
        )

    check_warehouse_access(
        db,
        current_user,
        order.warehouse_id,
    )

    refund.status = "Processed"
    refund.processed_by = current_user.id
    refund.processed_at = datetime.utcnow()

    if reason:
        refund.reason = reason

    db.commit()
    db.refresh(refund)

    try:
        record_audit(
            db=db,
            user_id=current_user.id,
            action="REFUND_PROCESSED",
            entity_type="Refund",
            entity_id=refund.id,
            metadata_json={
                "order_id": refund.order_id,
                "customer_id": refund.customer_id,
                "amount": str(refund.amount),
                "status": "Processed",
                "reason": reason,
            },
        )
    except Exception:
        pass

    return refund

def get_refund(
    db: Session,
    refund_id: int,
    current_user: User,
):
    refund = get_refund_by_id(db, refund_id)

    if not refund:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Refund not found",
        )

    if current_user.id == refund.customer_id:
        return refund

    if current_user.role.name == "Admin":
        return refund

    order = (
        db.query(Order)
        .filter(Order.id == refund.order_id)
        .first()
    )

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    check_warehouse_access(
        db,
        current_user,
        order.warehouse_id,
    )

    return refund

def list_my_refunds(
    db: Session,
    current_user: User,
):
    return get_customer_refunds(
        db,
        current_user.id,
    )