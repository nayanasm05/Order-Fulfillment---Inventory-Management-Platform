from sqlalchemy.orm import Session
from app.models import Refund


def create_refund(db: Session, refund: Refund):
    db.add(refund)
    db.flush()
    return refund


def get_refund_by_id(db: Session, refund_id: int):
    return (
        db.query(Refund)
        .filter(Refund.id == refund_id)
        .first()
    )


def get_refund_by_return_id(db: Session, return_request_id: int):
    return (
        db.query(Refund)
        .filter(Refund.return_request_id == return_request_id)
        .first()
    )


def get_customer_refunds(db: Session, customer_id: int):
    return (
        db.query(Refund)
        .filter(Refund.customer_id == customer_id)
        .order_by(Refund.created_at.desc())
        .all()
    )