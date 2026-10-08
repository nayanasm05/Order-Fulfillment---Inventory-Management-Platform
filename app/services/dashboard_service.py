from datetime import datetime, time
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import Inventory, Order, WarehouseUser


def get_role_name(current_user):
    if not current_user.role:
        return ""
    return current_user.role.name.lower().strip()


def get_manager_warehouse_ids(db: Session, user_id: int):
    return [
        row[0]
        for row in db.query(WarehouseUser.warehouse_id)
        .filter(WarehouseUser.user_id == user_id)
        .all()
    ]


def get_admin_dashboard(db: Session):
    total_orders = db.query(func.count(Order.id)).scalar() or 0

    pending_orders = (
        db.query(func.count(Order.id))
        .filter(Order.status == "Pending")
        .scalar()
        or 0
    )

    processing_orders = (
        db.query(func.count(Order.id))
        .filter(Order.status == "Processing")
        .scalar()
        or 0
    )

    completed_orders = (
        db.query(func.count(Order.id))
        .filter(Order.status == "Delivered")
        .scalar()
        or 0
    )

    cancelled_orders = (
        db.query(func.count(Order.id))
        .filter(Order.status == "Cancelled")
        .scalar()
        or 0
    )

    total_revenue = (
        db.query(func.coalesce(func.sum(Order.total_amount), 0))
        .filter(Order.status == "Delivered")
        .scalar()
        or Decimal("0.00")
    )

    low_stock_products = (
        db.query(func.count(func.distinct(Inventory.product_id)))
        .filter(
            (Inventory.quantity - Inventory.reserved_quantity)
            <= Inventory.reorder_level
        )
        .scalar()
        or 0
    )

    out_of_stock_products = (
        db.query(func.count(func.distinct(Inventory.product_id)))
        .filter(
            (Inventory.quantity - Inventory.reserved_quantity)
            <= 0
        )
        .scalar()
        or 0
    )

    return {
        "total_orders": total_orders,
        "pending_orders": pending_orders,
        "processing_orders": processing_orders,
        "completed_orders": completed_orders,
        "cancelled_orders": cancelled_orders,
        "total_revenue": float(total_revenue),
        "low_stock_products": low_stock_products,
        "out_of_stock_products": out_of_stock_products,
    }


def get_warehouse_manager_dashboard(
    db: Session,
    user_id: int,
):
    warehouse_ids = get_manager_warehouse_ids(
        db=db,
        user_id=user_id,
    )

    if not warehouse_ids:
        return {
            "warehouse_inventory": 0,
            "pending_fulfillment": 0,
            "processing_orders": 0,
            "low_stock_items": 0,
            "todays_shipments": 0,
            "warehouse_ids": [],
        }

    warehouse_inventory = (
        db.query(
            func.coalesce(
                func.sum(
                    Inventory.quantity
                    - Inventory.reserved_quantity
                ),
                0,
            )
        )
        .filter(
            Inventory.warehouse_id.in_(warehouse_ids)
        )
        .scalar()
        or 0
    )

    pending_fulfillment = (
        db.query(func.count(Order.id))
        .filter(
            Order.warehouse_id.in_(warehouse_ids),
            Order.status.in_(["Pending", "Confirmed"]),
        )
        .scalar()
        or 0
    )

    processing_orders = (
        db.query(func.count(Order.id))
        .filter(
            Order.warehouse_id.in_(warehouse_ids),
            Order.status == "Processing",
        )
        .scalar()
        or 0
    )

    low_stock_items = (
        db.query(func.count(Inventory.id))
        .filter(
            Inventory.warehouse_id.in_(warehouse_ids),
            (
                Inventory.quantity
                - Inventory.reserved_quantity
            )
            <= Inventory.reorder_level,
        )
        .scalar()
        or 0
    )

    start_of_day = datetime.combine(
        datetime.utcnow().date(),
        time.min,
    )

    end_of_day = datetime.combine(
        datetime.utcnow().date(),
        time.max,
    )

    todays_shipments = (
        db.query(func.count(Order.id))
        .filter(
            Order.warehouse_id.in_(warehouse_ids),
            Order.status == "Shipped",
            Order.updated_at >= start_of_day,
            Order.updated_at <= end_of_day,
        )
        .scalar()
        or 0
    )

    return {
        "warehouse_inventory": warehouse_inventory,
        "pending_fulfillment": pending_fulfillment,
        "processing_orders": processing_orders,
        "low_stock_items": low_stock_items,
        "todays_shipments": todays_shipments,
        "warehouse_ids": warehouse_ids,
    }


def get_customer_dashboard(
    db: Session,
    customer_id: int,
):
    total_orders = (
        db.query(func.count(Order.id))
        .filter(Order.customer_id == customer_id)
        .scalar()
        or 0
    )

    active_orders = (
        db.query(func.count(Order.id))
        .filter(
            Order.customer_id == customer_id,
            Order.status.notin_(
                ["Delivered", "Cancelled", "Failed", "Returned"]
            ),
        )
        .scalar()
        or 0
    )

    completed_orders = (
        db.query(func.count(Order.id))
        .filter(
            Order.customer_id == customer_id,
            Order.status == "Delivered",
        )
        .scalar()
        or 0
    )

    cancelled_orders = (
        db.query(func.count(Order.id))
        .filter(
            Order.customer_id == customer_id,
            Order.status == "Cancelled",
        )
        .scalar()
        or 0
    )

    total_spending = (
        db.query(func.coalesce(func.sum(Order.total_amount), 0))
        .filter(
            Order.customer_id == customer_id,
            Order.status.notin_(["Cancelled", "Failed"]),
        )
        .scalar()
        or Decimal("0.00")
    )

    return {
        "total_orders": total_orders,
        "active_orders": active_orders,
        "completed_orders": completed_orders,
        "cancelled_orders": cancelled_orders,
        "total_spending": float(total_spending),
    }


def get_dashboard_summary(
    db: Session,
    current_user,
):
    role = get_role_name(current_user)

    if role == "admin":
        return {
            "role": "Admin",
            "dashboard": get_admin_dashboard(db),
        }

    if role == "warehouse manager":
        return {
            "role": "Warehouse Manager",
            "dashboard": get_warehouse_manager_dashboard(
                db=db,
                user_id=current_user.id,
            ),
        }

    if role == "customer":
        return {
            "role": "Customer",
            "dashboard": get_customer_dashboard(
                db=db,
                customer_id=current_user.id,
            ),
        }

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Dashboard access denied for this role",
    )