from datetime import datetime

from decimal import Decimal, ROUND_HALF_UP

from uuid import uuid4

from fastapi import HTTPException, status

from sqlalchemy.orm import Session

from app.models import (

    Inventory,

    InventoryTransaction,

    Order,

    OrderItem,

    OrderStatusHistory,

    Product,

    Warehouse,

)

from app.repositories.order_repository import (

    create_order,

    create_order_item,

    create_order_status_history,

    get_all_orders,

    get_order_by_id,

    get_orders_by_customer,

    get_orders_by_warehouse,

)

from app.schemas import OrderCreate

from app.services.audit_service import record_audit
from app.services.notification_helper import (

    notify_order_cancelled,

    notify_order_created,

    notify_order_confirmed,

    notify_order_delivered,

    notify_failed_order_processing,

    notify_order_shipped,

)

# ============================================================

# ORDER STATUS

# ============================================================

ORDER_STATUSES = {

    "Pending",

    "Confirmed",

    "Processing",

    "Packed",

    "Shipped",

    "Delivered",

    "Cancelled",

    "Failed",

    "Returned",

}

ALLOWED_STATUS_TRANSITIONS = {

    "Pending": {

        "Confirmed",

        "Cancelled",

        "Failed",

    },

    "Confirmed": {

        "Processing",

        "Cancelled",

        "Failed",

    },

    "Processing": {

        "Packed",

        "Cancelled",

        "Failed",

    },

    "Packed": {

        "Shipped",

        "Cancelled",

    },

    "Shipped": {

        "Delivered",

        "Returned",

    },

    "Delivered": {

        "Returned",

    },

    "Cancelled": set(),

    "Failed": set(),

    "Returned": set(),

}

# ============================================================

# MONEY HELPERS

# ============================================================

def money(value: Decimal) -> Decimal:

    return Decimal(value).quantize(

        Decimal("0.01"),

        rounding=ROUND_HALF_UP,

    )

# ============================================================

# ORDER NUMBER

# ============================================================

def generate_order_number() -> str:

    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")

    unique_part = uuid4().hex[:8].upper()

    return f"ORD-{timestamp}-{unique_part}"

# ============================================================

# GET ORDER

# ============================================================

def get_order(

    db: Session,

    order_id: int,

):

    order = get_order_by_id(

        db=db,

        order_id=order_id,

    )

    if order is None:

        raise HTTPException(

            status_code=status.HTTP_404_NOT_FOUND,

            detail="Order not found",

        )

    return order

# ============================================================

# LIST CUSTOMER ORDERS

# ============================================================

def get_customer_orders(

    db: Session,

    customer_id: int,

):

    return get_orders_by_customer(

        db=db,

        customer_id=customer_id,

    )

# ============================================================

# LIST ALL ORDERS

# ============================================================

def get_orders(

    db: Session,

):

    return get_all_orders(db=db)

# ============================================================

# LIST WAREHOUSE ORDERS

# ============================================================

def get_warehouse_orders(

    db: Session,

    warehouse_id: int,

):

    return get_orders_by_warehouse(

        db=db,

        warehouse_id=warehouse_id,

    )

# ============================================================

# CREATE ORDER

# ============================================================

def create_new_order(

    db: Session,

    customer_id: int,

    order_data: OrderCreate,

):

    try:

        # ----------------------------------------------------

        # Validate warehouse

        # ----------------------------------------------------

        warehouse = (

            db.query(Warehouse)

            .filter(

                Warehouse.id == order_data.warehouse_id

            )

            .first()

        )

        if warehouse is None:

            raise HTTPException(

                status_code=status.HTTP_404_NOT_FOUND,

                detail="Warehouse not found",

            )

        if not warehouse.is_active:

            raise HTTPException(

                status_code=status.HTTP_400_BAD_REQUEST,

                detail="Warehouse is inactive",

            )

        # ----------------------------------------------------

        # Prevent duplicate products in same order

        # ----------------------------------------------------

        product_ids = [

            item.product_id

            for item in order_data.items

        ]

        if len(product_ids) != len(set(product_ids)):

            raise HTTPException(

                status_code=status.HTTP_400_BAD_REQUEST,

                detail="The same product cannot appear more than once in an order",

            )

        # ----------------------------------------------------

        # Validate order-level discount/tax

        # ----------------------------------------------------

        discount = money(

            Decimal(str(order_data.discount))

        )

        tax = money(

            Decimal(str(order_data.tax))

        )

        # ----------------------------------------------------

        # First create the order object

        # ----------------------------------------------------

        order = Order(

            order_number=generate_order_number(),

            customer_id=customer_id,

            warehouse_id=order_data.warehouse_id,

            subtotal=Decimal("0.00"),

            discount=discount,

            tax=tax,

            total_amount=Decimal("0.00"),

            status="Pending",

            payment_status="Pending",

            expected_delivery=order_data.expected_delivery,

        )

        create_order(

            db=db,

            order=order,

        )

        subtotal = Decimal("0.00")

        # ----------------------------------------------------

        # Process each product

        # ----------------------------------------------------

        for item_data in order_data.items:

            product = (

                db.query(Product)

                .filter(

                    Product.id == item_data.product_id

                )

                .first()

            )

            if product is None:

                raise HTTPException(

                    status_code=status.HTTP_404_NOT_FOUND,

                    detail=(

                        f"Product {item_data.product_id} "

                        "not found"

                    ),

                )

            # Inactive products cannot be ordered

            if not product.is_active:

                raise HTTPException(

                    status_code=status.HTTP_400_BAD_REQUEST,

                    detail=(

                        f"Product {product.id} "

                        "is inactive and cannot be added to a new order"

                    ),

                )

            # ------------------------------------------------

            # Lock inventory row

            # ------------------------------------------------

            inventory = (

                db.query(Inventory)

                .filter(

                    Inventory.product_id == product.id,

                    Inventory.warehouse_id

                    == order_data.warehouse_id,

                )

                .with_for_update()

                .first()

            )

            if inventory is None:

                raise HTTPException(

                    status_code=status.HTTP_400_BAD_REQUEST,

                    detail=(

                        f"No inventory found for product "

                        f"{product.id} in warehouse "

                        f"{order_data.warehouse_id}"

                    ),

                )

            # ------------------------------------------------

            # Calculate available quantity

            # ------------------------------------------------

            available_quantity = (

                inventory.quantity

                - inventory.reserved_quantity

            )

            if item_data.quantity > available_quantity:

                raise HTTPException(

                    status_code=status.HTTP_400_BAD_REQUEST,

                    detail=(

                        f"Insufficient inventory for product "

                        f"{product.id}. Available: "

                        f"{available_quantity}, requested: "

                        f"{item_data.quantity}"

                    ),

                )

            # ------------------------------------------------

            # PRICE SNAPSHOT

            # ------------------------------------------------

            unit_price = money(

                Decimal(str(product.price))

            )

            item_discount = Decimal("0.00")

            item_tax = Decimal("0.00")

            item_subtotal = money(

                unit_price

                * Decimal(item_data.quantity)

            )

            item_total = money(

                item_subtotal

                - item_discount

                + item_tax

            )

            # ------------------------------------------------

            # Create order item

            # ------------------------------------------------

            order_item = OrderItem(

                order=order,

                product_id=product.id,

                quantity=item_data.quantity,

                unit_price=unit_price,

                discount=item_discount,

                tax=item_tax,

                total_amount=item_total,

            )

            create_order_item(

                db=db,

                order_item=order_item,

            )

            subtotal += item_subtotal

            # ------------------------------------------------

            # RESERVE INVENTORY

            # ------------------------------------------------

            inventory.reserved_quantity += (

                item_data.quantity

            )

            # ------------------------------------------------

            # Inventory transaction

            # ------------------------------------------------

            inventory_transaction = InventoryTransaction(

                product_id=product.id,

                warehouse_id=order_data.warehouse_id,

                transaction_type="RESERVATION",

                quantity=item_data.quantity,

                reference_id=order.order_number,

                user_id=customer_id,

                reason="Inventory reserved for order",

                metadata_json=(

                    '{"order_id": '

                    f'"{order.id}", '

                    '"operation": "order_creation"}'

                ),

            )

            db.add(inventory_transaction)

        # ----------------------------------------------------

        # Calculate order total

        # ----------------------------------------------------

        subtotal = money(subtotal)

        if discount > subtotal:

            raise HTTPException(

                status_code=status.HTTP_400_BAD_REQUEST,

                detail="Discount cannot be greater than subtotal",

            )

        total_amount = money(

            subtotal

            - discount

            + tax

        )

        if total_amount < Decimal("0.00"):

            raise HTTPException(

                status_code=status.HTTP_400_BAD_REQUEST,

                detail="Order total cannot be negative",

            )

        order.subtotal = subtotal

        order.total_amount = total_amount

        # ----------------------------------------------------

        # Initial status history

        # ----------------------------------------------------

        status_history = OrderStatusHistory(

            order=order,

            old_status=None,

            new_status="Pending",

            changed_by=customer_id,

            reason="Order created",

        )

        create_order_status_history(

            db=db,

            status_history=status_history,

        )

        # ----------------------------------------------------

        # Commit everything together

        # ----------------------------------------------------

        db.commit()

        db.refresh(order)

        record_audit(
            db=db,
            user_id=customer_id,
            action="ORDER_CREATED",
            entity_type="Order",
            entity_id=order.id,
            metadata_json={
                "order_number": order.order_number,
                "warehouse_id": order.warehouse_id,
                "total_amount": str(order.total_amount),
            },
        )

        try:

            notify_order_created(

                db=db,

                user_id=order.customer_id,

                order_id=order.id,

                order_number=order.order_number,

            )

        except Exception:

            pass

        return order

    except HTTPException:

        db.rollback()

        raise

    except Exception:

        db.rollback()

        raise

# ============================================================

# UPDATE ORDER STATUS

# ============================================================

def update_order_status(

    db: Session,

    order_id: int,

    new_status: str,

    changed_by: int,

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

    new_status = new_status.strip()

    if new_status not in ORDER_STATUSES:

        raise HTTPException(

            status_code=status.HTTP_400_BAD_REQUEST,

            detail=(

                f"Invalid order status '{new_status}'. "

                f"Allowed statuses: "

                f"{', '.join(sorted(ORDER_STATUSES))}"

            ),

        )

    current_status = order.status

    if new_status == current_status:

        raise HTTPException(

            status_code=status.HTTP_400_BAD_REQUEST,

            detail="Order is already in this status",

        )

    allowed_statuses = ALLOWED_STATUS_TRANSITIONS.get(

        current_status,

        set(),

    )

    if new_status not in allowed_statuses:

        raise HTTPException(

            status_code=status.HTTP_400_BAD_REQUEST,

            detail=(

                f"Invalid order status transition: "

                f"{current_status} -> {new_status}"

            ),

        )

    # --------------------------------------------------------

    # Cancellation is handled separately

    # --------------------------------------------------------

    if new_status == "Cancelled":

        return cancel_existing_order(

            db=db,

            order_id=order_id,

            cancelled_by=changed_by,

            reason=reason or "Order cancelled",

        )

    try:

        order.status = new_status

        history = OrderStatusHistory(

            order_id=order.id,

            old_status=current_status,

            new_status=new_status,

            changed_by=changed_by,

            reason=reason,

        )

        create_order_status_history(

            db=db,

            status_history=history,

        )

        db.commit()

        db.refresh(order)

        record_audit(
            db=db,
            user_id=changed_by,
            action=f"ORDER_STATUS_{new_status.upper()}",
            entity_type="Order",
            entity_id=order.id,
            metadata_json={
                "order_number": order.order_number,
                "old_status": current_status,
                "new_status": new_status,
                "reason": reason,
            },
        )

        try:

            if new_status == "Confirmed":

                notify_order_confirmed(

                    db=db,

                    user_id=order.customer_id,

                    order_id=order.id,

                    order_number=order.order_number,

                )

            elif new_status == "Shipped":

                notify_order_shipped(

                    db=db,

                    user_id=order.customer_id,

                    order_id=order.id,

                    order_number=order.order_number,

                )

            elif new_status == "Delivered":

                notify_order_delivered(

                    db=db,

                    user_id=order.customer_id,

                    order_id=order.id,

                    order_number=order.order_number,

                )

            elif new_status == "Failed":

                notify_failed_order_processing(

                    db=db,

                    user_id=order.customer_id,

                    order_id=order.id,

                    order_number=order.order_number,

                    reason=reason or "Order processing failed",

                )

        except Exception:

            pass

        return order

    except Exception:

        db.rollback()

        raise

# ============================================================

# CANCEL ORDER

# ============================================================

def cancel_existing_order(

    db: Session,

    order_id: int,

    cancelled_by: int,

    reason: str,

):

    try:

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

        current_status = order.status

        if current_status == "Cancelled":

            raise HTTPException(

                status_code=status.HTTP_400_BAD_REQUEST,

                detail="Order is already cancelled",

            )

        allowed_statuses = ALLOWED_STATUS_TRANSITIONS.get(

            current_status,

            set(),

        )

        if "Cancelled" not in allowed_statuses:

            raise HTTPException(

                status_code=status.HTTP_400_BAD_REQUEST,

                detail=(

                    f"Order cannot be cancelled from "

                    f"status '{current_status}'"

                ),

            )

        # ----------------------------------------------------

        # Get order items

        # ----------------------------------------------------

        order_items = (

            db.query(OrderItem)

            .filter(

                OrderItem.order_id == order.id

            )

            .all()

        )

        # ----------------------------------------------------

        # Release reserved inventory

        # ----------------------------------------------------

        for order_item in order_items:

            inventory = (

                db.query(Inventory)

                .filter(

                    Inventory.product_id

                    == order_item.product_id,

                    Inventory.warehouse_id

                    == order.warehouse_id,

                )

                .with_for_update()

                .first()

            )

            if inventory is None:

                raise HTTPException(

                    status_code=status.HTTP_400_BAD_REQUEST,

                    detail=(

                        f"Inventory not found for "

                        f"product {order_item.product_id}"

                    ),

                )

            if (

                inventory.reserved_quantity

                < order_item.quantity

            ):

                raise HTTPException(

                    status_code=status.HTTP_400_BAD_REQUEST,

                    detail=(

                        f"Reserved inventory is insufficient "

                        f"for product {order_item.product_id}"

                    ),

                )

            inventory.reserved_quantity -= (

                order_item.quantity

            )

            # ------------------------------------------------

            # RELEASE transaction

            # ------------------------------------------------

            release_transaction = InventoryTransaction(

                product_id=order_item.product_id,

                warehouse_id=order.warehouse_id,

                transaction_type="RELEASE",

                quantity=order_item.quantity,

                reference_id=order.order_number,

                user_id=cancelled_by,

                reason=(

                    f"Inventory released because "

                    f"order {order.order_number} was cancelled"

                ),

                metadata_json=(

                    '{"order_id": '

                    f'"{order.id}", '

                    '"operation": "order_cancellation"}'

                ),

            )

            db.add(release_transaction)

        # ----------------------------------------------------

        # Change order status

        # ----------------------------------------------------

        order.status = "Cancelled"

        # ----------------------------------------------------

        # Status history

        # ----------------------------------------------------

        history = OrderStatusHistory(

            order_id=order.id,

            old_status=current_status,

            new_status="Cancelled",

            changed_by=cancelled_by,

            reason=reason,

        )

        create_order_status_history(

            db=db,

            status_history=history,

        )

        # ----------------------------------------------------

        # Commit entire cancellation transaction

        # ----------------------------------------------------

        db.commit()

        db.refresh(order)

        record_audit(
            db=db,
            user_id=cancelled_by,
            action="ORDER_CANCELLED",
            entity_type="Order",
            entity_id=order.id,
            metadata_json={
                "order_number": order.order_number,
                "previous_status": current_status,
                "reason": reason,
            },
        )

        try:

            notify_order_cancelled(

                db=db,

                user_id=order.customer_id,

                order_id=order.id,

                order_number=order.order_number,

            )

        except Exception:

            pass

        return order

    except HTTPException:

        db.rollback()

        raise

    except Exception:

        db.rollback()

        raise