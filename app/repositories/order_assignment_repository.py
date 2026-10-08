from sqlalchemy.orm import Session

from app.models import OrderAssignment


def create_assignment(db: Session, assignment: OrderAssignment):
    db.add(assignment)
    db.flush()
    return assignment


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


def get_assignment_by_id(db: Session, assignment_id: int):
    return (
        db.query(OrderAssignment)
        .filter(OrderAssignment.id == assignment_id)
        .first()
    )


def get_order_assignments(db: Session, order_id: int):
    return (
        db.query(OrderAssignment)
        .filter(OrderAssignment.order_id == order_id)
        .order_by(OrderAssignment.assigned_at.desc())
        .all()
    )


def deactivate_assignment(assignment: OrderAssignment):
    assignment.is_active = False