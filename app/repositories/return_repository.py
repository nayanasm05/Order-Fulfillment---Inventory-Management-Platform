from sqlalchemy.orm import Session

from app.models import ReturnRequest


def create_return(db: Session, return_request: ReturnRequest):
    db.add(return_request)
    db.flush()
    return return_request


def get_return_by_id(db: Session, return_id: int):
    return (
        db.query(ReturnRequest)
        .filter(ReturnRequest.id == return_id)
        .first()
    )


def get_returns_for_order(db: Session, order_id: int):
    return (
        db.query(ReturnRequest)
        .filter(ReturnRequest.order_id == order_id)
        .order_by(ReturnRequest.created_at.desc())
        .all()
    )


def get_returns_for_customer(db: Session, customer_id: int):
    return (
        db.query(ReturnRequest)
        .filter(ReturnRequest.customer_id == customer_id)
        .order_by(ReturnRequest.created_at.desc())
        .all()
    )


def get_existing_return_quantity(
    db: Session,
    order_item_id: int,
):
    result = (
        db.query(ReturnRequest)
        .filter(
            ReturnRequest.order_item_id == order_item_id,
            ReturnRequest.status.in_(
                ["Requested", "Approved", "Processed"]
            ),
        )
        .all()
    )

    return sum(item.quantity for item in result)