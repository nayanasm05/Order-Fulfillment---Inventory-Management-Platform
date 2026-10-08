from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import (
    Inventory,
    InventoryTransaction,
    Product,
    Warehouse,
)
from app.repositories.inventory_repository import (
    create_inventory,
    get_inventory_by_id,
    get_inventory_by_product_and_warehouse,
    update_inventory,
)
from app.services.audit_service import record_audit
from app.services.notification_helper import notify_user


def create_new_inventory(
    db: Session,
    product_id: int,
    warehouse_id: int,
    quantity: int,
    reorder_level: int,
):
    product = (
        db.query(Product)
        .filter(Product.id == product_id)
        .first()
    )

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    warehouse = (
        db.query(Warehouse)
        .filter(Warehouse.id == warehouse_id)
        .first()
    )

    if not warehouse:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Warehouse not found",
        )

    if not warehouse.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Warehouse is inactive",
        )

    if quantity < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Quantity cannot be negative",
        )

    if reorder_level < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reorder level cannot be negative",
        )

    existing_inventory = get_inventory_by_product_and_warehouse(
        db,
        product_id,
        warehouse_id,
    )

    if existing_inventory:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Inventory already exists for this product and warehouse",
        )

    inventory = Inventory(
        product_id=product_id,
        warehouse_id=warehouse_id,
        quantity=quantity,
        reserved_quantity=0,
        reorder_level=reorder_level,
    )

    result = create_inventory(db, inventory)

    try:
        record_audit(
            db=db,
            user_id=None,
            action="INVENTORY_CREATED",
            entity_type="Inventory",
            entity_id=result.id,
            metadata_json={
                "product_id": product_id,
                "warehouse_id": warehouse_id,
                "quantity": quantity,
                "reorder_level": reorder_level,
            },
        )
    except Exception:
        pass

    return result


def update_existing_inventory(
    db: Session,
    inventory_id: int,
    quantity: int | None = None,
    reserved_quantity: int | None = None,
    reorder_level: int | None = None,
):
    inventory = get_inventory_by_id(
        db,
        inventory_id,
    )

    if not inventory:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inventory not found",
        )

    if quantity is not None:
        if quantity < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Quantity cannot be negative",
            )

        if quantity < inventory.reserved_quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Quantity cannot be less than reserved quantity",
            )

        inventory.quantity = quantity

    if reserved_quantity is not None:
        if reserved_quantity < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reserved quantity cannot be negative",
            )

        if reserved_quantity > inventory.quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reserved quantity cannot exceed quantity",
            )

        inventory.reserved_quantity = reserved_quantity

    if reorder_level is not None:
        if reorder_level < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reorder level cannot be negative",
            )

        inventory.reorder_level = reorder_level

    result = update_inventory(
        db,
        inventory,
    )

    try:
        record_audit(
            db=db,
            user_id=None,
            action="INVENTORY_UPDATED",
            entity_type="Inventory",
            entity_id=result.id,
            metadata_json={
                "product_id": result.product_id,
                "warehouse_id": result.warehouse_id,
                "quantity": result.quantity,
                "reserved_quantity": result.reserved_quantity,
                "reorder_level": result.reorder_level,
            },
        )
    except Exception:
        pass

    return result


def adjust_inventory(
    db: Session,
    inventory_id: int,
    adjustment_quantity: int,
    reason: str,
    user_id: int,
):
    inventory = (
        db.query(Inventory)
        .filter(Inventory.id == inventory_id)
        .with_for_update()
        .first()
    )

    if not inventory:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inventory not found",
        )

    previous_quantity = inventory.quantity
    previous_available_quantity = (
        previous_quantity - inventory.reserved_quantity
    )
    new_quantity = previous_quantity + adjustment_quantity

    if new_quantity < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inventory quantity cannot become negative",
        )

    if new_quantity < inventory.reserved_quantity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inventory quantity cannot be less than reserved quantity",
        )

    inventory.quantity = new_quantity

    transaction = InventoryTransaction(
        product_id=inventory.product_id,
        warehouse_id=inventory.warehouse_id,
        transaction_type="ADJUSTMENT",
        quantity=adjustment_quantity,
        user_id=user_id,
        reason=reason,
        reference_id=str(inventory.id),
        metadata_json=(
            f'{{"previous_quantity": {previous_quantity}, '
            f'"new_quantity": {new_quantity}}}'
        ),
    )

    db.add(transaction)
    db.commit()
    db.refresh(inventory)

    try:
        record_audit(
            db=db,
            user_id=user_id,
            action="INVENTORY_ADJUSTED",
            entity_type="Inventory",
            entity_id=inventory.id,
            metadata_json={
                "product_id": inventory.product_id,
                "warehouse_id": inventory.warehouse_id,
                "previous_quantity": previous_quantity,
                "new_quantity": new_quantity,
                "adjustment_quantity": adjustment_quantity,
                "reason": reason,
            },
        )
    except Exception:
        pass

    new_available_quantity = (
        inventory.quantity - inventory.reserved_quantity
    )

    if (
        previous_available_quantity > inventory.reorder_level
        and new_available_quantity <= inventory.reorder_level
    ):
        try:
            notify_user(
                db=db,
                user_id=user_id,
                title="Low Stock Alert",
                message=(
                    f"Product {inventory.product_id} in warehouse "
                    f"{inventory.warehouse_id} has reached the reorder level. "
                    f"Available quantity: {new_available_quantity}, "
                    f"reorder level: {inventory.reorder_level}."
                ),
                notification_type="low_stock",
                reference_type="inventory",
                reference_id=inventory.id,
            )
        except Exception:
            pass

    return inventory


def transfer_inventory(
    db: Session,
    product_id: int,
    from_warehouse_id: int,
    to_warehouse_id: int,
    quantity: int,
    reason: str,
    user_id: int,
):
    if from_warehouse_id == to_warehouse_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Source and destination warehouses must be different",
        )

    source_warehouse = (
        db.query(Warehouse)
        .filter(Warehouse.id == from_warehouse_id)
        .first()
    )

    if not source_warehouse:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source warehouse not found",
        )

    if not source_warehouse.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Source warehouse is inactive",
        )

    destination_warehouse = (
        db.query(Warehouse)
        .filter(Warehouse.id == to_warehouse_id)
        .first()
    )

    if not destination_warehouse:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Destination warehouse not found",
        )

    if not destination_warehouse.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Destination warehouse is inactive",
        )

    product = (
        db.query(Product)
        .filter(Product.id == product_id)
        .first()
    )

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    source_inventory = (
        db.query(Inventory)
        .filter(
            Inventory.product_id == product_id,
            Inventory.warehouse_id == from_warehouse_id,
        )
        .with_for_update()
        .first()
    )

    if not source_inventory:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source inventory not found",
        )

    available_quantity = (
        source_inventory.quantity
        - source_inventory.reserved_quantity
    )

    if available_quantity < quantity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Insufficient available inventory for transfer",
        )

    destination_inventory = (
        db.query(Inventory)
        .filter(
            Inventory.product_id == product_id,
            Inventory.warehouse_id == to_warehouse_id,
        )
        .with_for_update()
        .first()
    )

    if not destination_inventory:
        destination_inventory = Inventory(
            product_id=product_id,
            warehouse_id=to_warehouse_id,
            quantity=0,
            reserved_quantity=0,
            reorder_level=0,
        )
        db.add(destination_inventory)
        db.flush()

    source_inventory.quantity -= quantity
    destination_inventory.quantity += quantity

    transfer_out = InventoryTransaction(
        product_id=product_id,
        warehouse_id=from_warehouse_id,
        transaction_type="TRANSFER_OUT",
        quantity=quantity,
        user_id=user_id,
        reason=reason,
        reference_id=(
            f"TRANSFER-{from_warehouse_id}-{to_warehouse_id}"
        ),
    )

    transfer_in = InventoryTransaction(
        product_id=product_id,
        warehouse_id=to_warehouse_id,
        transaction_type="TRANSFER_IN",
        quantity=quantity,
        user_id=user_id,
        reason=reason,
        reference_id=(
            f"TRANSFER-{from_warehouse_id}-{to_warehouse_id}"
        ),
    )

    db.add(transfer_out)
    db.add(transfer_in)
    db.commit()

    db.refresh(source_inventory)
    db.refresh(destination_inventory)

    try:
        record_audit(
            db=db,
            user_id=user_id,
            action="INVENTORY_TRANSFER",
            entity_type="Inventory",
            entity_id=source_inventory.id,
            metadata_json={
                "product_id": product_id,
                "from_warehouse_id": from_warehouse_id,
                "to_warehouse_id": to_warehouse_id,
                "quantity": quantity,
                "reason": reason,
                "source_inventory_id": source_inventory.id,
                "destination_inventory_id": destination_inventory.id,
            },
        )
    except Exception:
        pass

    try:
        notify_user(
            db=db,
            user_id=user_id,
            title="Inventory Transfer",
            message=(
                f"Product {product_id} inventory transfer completed. "
                f"{quantity} units transferred from warehouse "
                f"{from_warehouse_id} to warehouse {to_warehouse_id}."
            ),
            notification_type="inventory_transfer",
            reference_type="inventory",
            reference_id=source_inventory.id,
        )
    except Exception:
        pass

    source_available_quantity = (
        source_inventory.quantity
        - source_inventory.reserved_quantity
    )

    if source_available_quantity <= source_inventory.reorder_level:
        try:
            notify_user(
                db=db,
                user_id=user_id,
                title="Low Stock Alert",
                message=(
                    f"Product {product_id} in warehouse "
                    f"{from_warehouse_id} is now at or below the "
                    f"reorder level. Available quantity: "
                    f"{source_available_quantity}, reorder level: "
                    f"{source_inventory.reorder_level}."
                ),
                notification_type="low_stock",
                reference_type="inventory",
                reference_id=source_inventory.id,
            )
        except Exception:
            pass

    return {
        "message": "Inventory transferred successfully",
        "product_id": product_id,
        "from_warehouse_id": from_warehouse_id,
        "to_warehouse_id": to_warehouse_id,
        "quantity": quantity,
        "source_inventory_id": source_inventory.id,
        "destination_inventory_id": destination_inventory.id,
    }


def reserve_inventory(
    db: Session,
    inventory_id: int,
    quantity: int,
    user_id: int,
    reference_id: str | None = None,
):
    inventory = (
        db.query(Inventory)
        .filter(Inventory.id == inventory_id)
        .with_for_update()
        .first()
    )

    if not inventory:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inventory not found",
        )

    available_quantity = (
        inventory.quantity - inventory.reserved_quantity
    )

    if quantity > available_quantity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Insufficient available inventory for reservation",
        )

    inventory.reserved_quantity += quantity

    transaction = InventoryTransaction(
        product_id=inventory.product_id,
        warehouse_id=inventory.warehouse_id,
        transaction_type="RESERVATION",
        quantity=quantity,
        user_id=user_id,
        reason="Inventory reserved",
        reference_id=reference_id,
    )

    db.add(transaction)
    db.commit()
    db.refresh(inventory)

    try:
        record_audit(
            db=db,
            user_id=user_id,
            action="INVENTORY_RESERVED",
            entity_type="Inventory",
            entity_id=inventory.id,
            metadata_json={
                "product_id": inventory.product_id,
                "warehouse_id": inventory.warehouse_id,
                "quantity": quantity,
                "reference_id": reference_id,
                "reserved_quantity": inventory.reserved_quantity,
            },
        )
    except Exception:
        pass

    return inventory


def release_inventory(
    db: Session,
    inventory_id: int,
    quantity: int,
    user_id: int,
    reference_id: str | None = None,
):
    inventory = (
        db.query(Inventory)
        .filter(Inventory.id == inventory_id)
        .with_for_update()
        .first()
    )

    if not inventory:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inventory not found",
        )

    if quantity > inventory.reserved_quantity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Release quantity cannot exceed reserved quantity",
        )

    inventory.reserved_quantity -= quantity

    transaction = InventoryTransaction(
        product_id=inventory.product_id,
        warehouse_id=inventory.warehouse_id,
        transaction_type="RELEASE",
        quantity=quantity,
        user_id=user_id,
        reason="Inventory reservation released",
        reference_id=reference_id,
    )

    db.add(transaction)
    db.commit()
    db.refresh(inventory)

    try:
        record_audit(
            db=db,
            user_id=user_id,
            action="INVENTORY_RELEASED",
            entity_type="Inventory",
            entity_id=inventory.id,
            metadata_json={
                "product_id": inventory.product_id,
                "warehouse_id": inventory.warehouse_id,
                "quantity": quantity,
                "reference_id": reference_id,
                "reserved_quantity": inventory.reserved_quantity,
            },
        )
    except Exception:
        pass

    return inventory