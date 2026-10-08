from sqlalchemy.orm import Session

from app.models import (
    Inventory,
    InventoryTransaction,
)


def get_inventory_by_id(
    db: Session,
    inventory_id: int,
):
    return (
        db.query(Inventory)
        .filter(Inventory.id == inventory_id)
        .first()
    )


def get_inventory_by_product_and_warehouse(
    db: Session,
    product_id: int,
    warehouse_id: int,
):
    return (
        db.query(Inventory)
        .filter(
            Inventory.product_id == product_id,
            Inventory.warehouse_id == warehouse_id,
        )
        .first()
    )


def get_inventory(
    db: Session,
):
    return (
        db.query(Inventory)
        .order_by(Inventory.id.desc())
        .all()
    )


def create_inventory(
    db: Session,
    inventory: Inventory,
):
    db.add(inventory)
    db.commit()
    db.refresh(inventory)

    return inventory


def update_inventory(
    db: Session,
    inventory: Inventory,
):
    db.commit()
    db.refresh(inventory)

    return inventory


def get_inventory_transactions(
    db: Session,
    inventory_id: int,
):
    inventory = (
        db.query(Inventory)
        .filter(Inventory.id == inventory_id)
        .first()
    )

    if not inventory:
        return None

    return (
        db.query(InventoryTransaction)
        .filter(
            InventoryTransaction.product_id == inventory.product_id,
            InventoryTransaction.warehouse_id == inventory.warehouse_id,
        )
        .order_by(
            InventoryTransaction.created_at.desc()
        )
        .all()
    )