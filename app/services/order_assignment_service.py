from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models import Order, OrderAssignment, User, WarehouseUser
from app.repositories.order_assignment_repository import (
    create_assignment,
    deactivate_assignment,
    get_active_assignment as repository_get_active_assignment,
    get_order_assignments,
)
from app.services.audit_service import record_audit
from app.services.notification_helper import notify_order_assigned

def _check_order_view_access(db: Session, order: Order, current_user: User):
    role_name = current_user.role.name.lower() if current_user.role else ""
    if role_name == "admin":
        return
    if role_name == "customer":
        if order.customer_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to view this order assignment",
            )
        return
    warehouse_access = db.query(WarehouseUser).filter(
        WarehouseUser.user_id == current_user.id,
        WarehouseUser.warehouse_id == order.warehouse_id,
    ).first()
    if warehouse_access is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to access this warehouse",
        )

def _check_order_manage_access(db: Session, order: Order, current_user: User):
    role_name = current_user.role.name.lower() if current_user.role else ""
    if role_name == "admin":
        return
    if role_name != "warehouse manager":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Admin or Warehouse Manager can assign orders",
        )
    warehouse_access = db.query(WarehouseUser).filter(
        WarehouseUser.user_id == current_user.id,
        WarehouseUser.warehouse_id == order.warehouse_id,
    ).first()
    if warehouse_access is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to manage this warehouse",
        )

def validate_fulfillment_agent(db: Session, order: Order, user_id: int):
    agent = db.query(User).filter(User.id == user_id).first()
    if agent is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fulfillment agent not found",
        )
    if not agent.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Fulfillment agent is inactive",
        )
    role_name = agent.role.name.lower() if agent.role else ""
    if role_name != "fulfillment agent":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not a Fulfillment Agent",
        )
    warehouse_access = db.query(WarehouseUser).filter(
        WarehouseUser.user_id == agent.id,
        WarehouseUser.warehouse_id == order.warehouse_id,
    ).first()
    if warehouse_access is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Fulfillment agent is not assigned to this warehouse",
        )
    return agent

def assign_order(
    db: Session,
    order_id: int,
    assigned_to: int,
    assigned_by: int,
    reason: str | None = None,
):
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
    assigner = db.query(User).filter(User.id == assigned_by).first()
    if assigner is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assigning user not found",
        )
    _check_order_manage_access(db, order, assigner)
    validate_fulfillment_agent(db, order, assigned_to)
    previous_assignment = repository_get_active_assignment(db, order_id)
    previous_assigned_to = previous_assignment.assigned_to if previous_assignment else None
    if previous_assignment:
        deactivate_assignment(previous_assignment)
    assignment = OrderAssignment(
        order_id=order_id,
        assigned_to=assigned_to,
        assigned_by=assigned_by,
        reason=reason,
        is_active=True,
    )
    create_assignment(db, assignment)
    db.commit()
    db.refresh(assignment)
    try:
        record_audit(
            db=db,
            user_id=assigned_by,
            action="ORDER_REASSIGNED" if previous_assignment else "ORDER_ASSIGNED",
            entity_type="OrderAssignment",
            entity_id=assignment.id,
            metadata_json={
                "order_id": order.id,
                "order_number": order.order_number,
                "assigned_to": assigned_to,
                "previous_assigned_to": previous_assigned_to,
                "reason": reason,
            },
        )
    except Exception:
        pass
    try:
        notify_order_assigned(
            db=db,
            user_id=assigned_to,
            order_id=order.id,
            order_number=order.order_number,
        )
    except Exception:
        pass
    return assignment

def reassign_order(
    db: Session,
    order_id: int,
    assigned_to: int,
    assigned_by: int,
    reason: str | None = None,
):
    return assign_order(
        db=db,
        order_id=order_id,
        assigned_to=assigned_to,
        assigned_by=assigned_by,
        reason=reason,
    )

def get_active_assignment(
    db: Session,
    order_id: int,
    current_user: User,
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )
    _check_order_view_access(db, order, current_user)
    assignment = repository_get_active_assignment(db, order_id)
    if assignment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active assignment found for this order",
        )
    return assignment

def get_assignment_history(
    db: Session,
    order_id: int,
    current_user: User,
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )
    _check_order_view_access(db, order, current_user)
    return get_order_assignments(db, order_id)