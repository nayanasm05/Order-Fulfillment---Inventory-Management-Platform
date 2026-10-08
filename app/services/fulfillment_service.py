from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models import Order, OrderAssignment, OrderStatusHistory, User, WarehouseUser
from app.services.audit_service import record_audit

FULFILLMENT_TRANSITIONS = {
    "Pending": "Confirmed",
    "Confirmed": "Processing",
    "Processing": "Packed",
    "Packed": "Shipped",
    "Shipped": "Delivered",
}

def get_order(db: Session, order_id: int):
    order = (
        db.query(Order)
        .filter(Order.id == order_id)
        .with_for_update()
        .first()
    )
    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )
    return order

def get_active_assignment(db: Session, order_id: int):
    return (
        db.query(OrderAssignment)
        .filter(
            OrderAssignment.order_id == order_id,
            OrderAssignment.is_active.is_(True),
        )
        .order_by(OrderAssignment.assigned_at.desc())
        .first()
    )

def check_warehouse_access(db: Session, current_user: User, warehouse_id: int):
    role_name = current_user.role.name.lower() if current_user.role else ""
    if role_name == "admin":
        return
    access = (
        db.query(WarehouseUser)
        .filter(
            WarehouseUser.user_id == current_user.id,
            WarehouseUser.warehouse_id == warehouse_id,
        )
        .first()
    )
    if access is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to access this warehouse",
        )

def check_fulfillment_access(db: Session, order: Order, current_user: User):
    role_name = current_user.role.name.lower() if current_user.role else ""
    if role_name == "admin":
        return
    if role_name == "warehouse manager":
        check_warehouse_access(db, current_user, order.warehouse_id)
        return
    if role_name != "fulfillment agent":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to perform fulfillment actions",
        )
    assignment = get_active_assignment(db, order.id)
    if assignment is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order has no active fulfillment assignment",
        )
    if assignment.assigned_to != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the assigned Fulfillment Agent can process this order",
        )
    check_warehouse_access(db, current_user, order.warehouse_id)

def update_fulfillment_status(
    db: Session,
    order_id: int,
    new_status: str,
    current_user: User,
):
    order = get_order(db, order_id)
    check_fulfillment_access(db, order, current_user)
    expected_status = FULFILLMENT_TRANSITIONS.get(order.status)
    if expected_status is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Order cannot move from {order.status}",
        )
    if expected_status != new_status:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid transition from {order.status} to {new_status}",
        )
    old_status = order.status
    order.status = new_status
    history = OrderStatusHistory(
        order_id=order.id,
        old_status=old_status,
        new_status=new_status,
        changed_by=current_user.id,
        reason="Fulfillment workflow update",
    )
    db.add(history)
    db.commit()
    db.refresh(order)
    try:
        record_audit(
            db=db,
            user_id=current_user.id,
            action=f"FULFILLMENT_{new_status.upper()}",
            entity_type="Order",
            entity_id=order.id,
            metadata_json={
                "order_number": order.order_number,
                "old_status": old_status,
                "new_status": new_status,
                "reason": "Fulfillment workflow update",
            },
        )
    except Exception:
        pass
    return order

def confirm_order(db: Session, order_id: int, current_user: User):
    return update_fulfillment_status(db, order_id, "Confirmed", current_user)

def start_processing(db: Session, order_id: int, current_user: User):
    return update_fulfillment_status(db, order_id, "Processing", current_user)

def pack_order(db: Session, order_id: int, current_user: User):
    return update_fulfillment_status(db, order_id, "Packed", current_user)

def ship_order(db: Session, order_id: int, current_user: User):
    return update_fulfillment_status(db, order_id, "Shipped", current_user)

def deliver_order(db: Session, order_id: int, current_user: User):
    return update_fulfillment_status(db, order_id, "Delivered", current_user)