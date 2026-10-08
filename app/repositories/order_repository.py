from sqlalchemy.orm import Session

from app.models import (
    Order,
    OrderItem,
    OrderStatusHistory,
)


# ============================================================
# CREATE ORDER
# ============================================================

def create_order(
    db: Session,
    order: Order,
):
    db.add(order)
    db.flush()

    return order


# ============================================================
# CREATE ORDER ITEM
# ============================================================

def create_order_item(
    db: Session,
    order_item: OrderItem,
):
    db.add(order_item)
    db.flush()

    return order_item


# ============================================================
# CREATE STATUS HISTORY
# ============================================================

def create_order_status_history(
    db: Session,
    status_history: OrderStatusHistory,
):
    db.add(status_history)
    db.flush()

    return status_history


# ============================================================
# GET ORDER BY ID
# ============================================================

def get_order_by_id(
    db: Session,
    order_id: int,
):
    return (
        db.query(Order)
        .filter(Order.id == order_id)
        .first()
    )


# ============================================================
# GET ORDER BY NUMBER
# ============================================================

def get_order_by_number(
    db: Session,
    order_number: str,
):
    return (
        db.query(Order)
        .filter(
            Order.order_number == order_number
        )
        .first()
    )


# ============================================================
# GET CUSTOMER ORDERS
# ============================================================

def get_orders_by_customer(
    db: Session,
    customer_id: int,
):
    return (
        db.query(Order)
        .filter(
            Order.customer_id == customer_id
        )
        .order_by(
            Order.created_at.desc()
        )
        .all()
    )


# ============================================================
# GET ALL ORDERS
# ============================================================

def get_all_orders(
    db: Session,
):
    return (
        db.query(Order)
        .order_by(
            Order.created_at.desc()
        )
        .all()
    )


# ============================================================
# GET ORDERS BY WAREHOUSE
# ============================================================

def get_orders_by_warehouse(
    db: Session,
    warehouse_id: int,
):
    return (
        db.query(Order)
        .filter(
            Order.warehouse_id == warehouse_id
        )
        .order_by(
            Order.created_at.desc()
        )
        .all()
    )


# ============================================================
# GET ORDER ITEMS
# ============================================================

def get_order_items(
    db: Session,
    order_id: int,
):
    return (
        db.query(OrderItem)
        .filter(
            OrderItem.order_id == order_id
        )
        .order_by(
            OrderItem.id.asc()
        )
        .all()
    )


# ============================================================
# GET ORDER STATUS HISTORY
# ============================================================

def get_order_status_history(
    db: Session,
    order_id: int,
):
    return (
        db.query(OrderStatusHistory)
        .filter(
            OrderStatusHistory.order_id == order_id
        )
        .order_by(
            OrderStatusHistory.created_at.asc()
        )
        .all()
    )


# ============================================================
# UPDATE ORDER
# ============================================================

def update_order(
    db: Session,
    order: Order,
):
    db.flush()
    db.refresh(order)

    return order


# ============================================================
# SAVE CHANGES
# ============================================================

def save_order_changes(
    db: Session,
):
    db.flush()


# ============================================================
# DELETE ORDER
# ============================================================

def delete_order(
    db: Session,
    order: Order,
):
    db.delete(order)
    db.flush()