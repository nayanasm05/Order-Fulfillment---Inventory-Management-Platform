from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy import asc, desc
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import check_warehouse_access, get_current_user
from app.models import Inventory, User, WarehouseUser
from app.repositories.inventory_repository import (
    get_inventory,
    get_inventory_by_id,
    get_inventory_transactions,
)
from app.services.idempotency_service import (
    get_idempotency_record,
    validate_idempotency_key,
    save_idempotency_record,
)
from app.schemas import (
    InventoryAdjustmentRequest,
    InventoryCreate,
    InventoryListPaginatedResponse,
    InventoryReleaseRequest,
    InventoryReservationRequest,
    InventoryResponse,
    InventoryTransactionResponse,
    InventoryTransferRequest,
    InventoryUpdate,
)
from app.services.inventory_service import (
    adjust_inventory,
    create_new_inventory,
    release_inventory,
    reserve_inventory,
    transfer_inventory,
    update_existing_inventory,
)

router = APIRouter(
    prefix="/api/inventory",
    tags=["Inventory"],
)


@router.post(
    "",
    response_model=InventoryResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_inventory(
    inventory_data: InventoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    check_warehouse_access(
        warehouse_id=inventory_data.warehouse_id,
        current_user=current_user,
        db=db,
    )

    return create_new_inventory(
        db=db,
        product_id=inventory_data.product_id,
        warehouse_id=inventory_data.warehouse_id,
        quantity=inventory_data.quantity,
        reorder_level=inventory_data.reorder_level,
    )


@router.get(
    "",
    response_model=InventoryListPaginatedResponse,
)
def list_inventory(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    warehouse_id: int | None = Query(None, ge=1),
    product_id: int | None = Query(None, ge=1),
    low_stock: bool = Query(False),
    out_of_stock: bool = Query(False),
    sort_by: str = Query(
        "updated_at",
        pattern="^(id|quantity|reserved_quantity|reorder_level|updated_at)$",
    ),
    sort_order: str = Query(
        "desc",
        pattern="^(asc|desc)$",
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    role_name = (
        current_user.role.name.lower()
        if current_user.role
        else ""
    )

    query = db.query(Inventory)

    if role_name == "admin":
        if warehouse_id is not None:
            query = query.filter(
                Inventory.warehouse_id == warehouse_id
            )
    else:
        assigned_warehouse_ids = [
            row[0]
            for row in db.query(
                WarehouseUser.warehouse_id
            )
            .filter(
                WarehouseUser.user_id == current_user.id
            )
            .all()
        ]

        if not assigned_warehouse_ids:
            return {
                "items": [],
                "pagination": {
                    "page": page,
                    "page_size": page_size,
                    "total": 0,
                    "total_pages": 0,
                },
            }

        if warehouse_id is not None:
            if warehouse_id not in assigned_warehouse_ids:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You are not authorized to access this warehouse",
                )

            query = query.filter(
                Inventory.warehouse_id == warehouse_id
            )
        else:
            query = query.filter(
                Inventory.warehouse_id.in_(
                    assigned_warehouse_ids
                )
            )

    if product_id is not None:
        query = query.filter(
            Inventory.product_id == product_id
        )

    available_quantity = (
        Inventory.quantity
        - Inventory.reserved_quantity
    )

    if low_stock:
        query = query.filter(
            available_quantity <= Inventory.reorder_level
        )

    if out_of_stock:
        query = query.filter(
            available_quantity <= 0
        )

    sort_column_map = {
        "id": Inventory.id,
        "quantity": Inventory.quantity,
        "reserved_quantity": Inventory.reserved_quantity,
        "reorder_level": Inventory.reorder_level,
        "updated_at": Inventory.updated_at,
    }

    sort_column = sort_column_map[sort_by]

    if sort_order == "asc":
        query = query.order_by(asc(sort_column))
    else:
        query = query.order_by(desc(sort_column))

    total = query.count()

    offset = (page - 1) * page_size

    inventory_items = (
        query
        .offset(offset)
        .limit(page_size)
        .all()
    )

    total_pages = (
        (total + page_size - 1) // page_size
        if total > 0
        else 0
    )

    return {
        "items": inventory_items,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": total_pages,
        },
    }


@router.get(
    "/{inventory_id}/transactions",
    response_model=list[InventoryTransactionResponse],
)
def get_inventory_transactions_api(
    inventory_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    inventory = get_inventory_by_id(
        db=db,
        inventory_id=inventory_id,
    )

    if inventory is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inventory not found",
        )

    check_warehouse_access(
        warehouse_id=inventory.warehouse_id,
        current_user=current_user,
        db=db,
    )

    transactions = get_inventory_transactions(
        db=db,
        inventory_id=inventory_id,
    )

    return transactions


@router.post(
    "/adjust",
    response_model=InventoryResponse,
)
@router.post(
    "/adjust",
    response_model=InventoryResponse,
)
def adjust_inventory_api(
    adjustment_data: InventoryAdjustmentRequest,
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    key = validate_idempotency_key(idempotency_key)

    existing = get_idempotency_record(
        db=db,
        key=key,
        user_id=current_user.id,
        endpoint="POST:/api/inventory/adjust",
    )

    if existing:
        if existing.response_body:
            return existing.response_body
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Idempotency key is already being processed",
        )

    inventory = get_inventory_by_id(
        db=db,
        inventory_id=adjustment_data.inventory_id,
    )

    if inventory is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inventory not found",
        )

    check_warehouse_access(
        warehouse_id=inventory.warehouse_id,
        current_user=current_user,
        db=db,
    )

    result = adjust_inventory(
        db=db,
        inventory_id=adjustment_data.inventory_id,
        adjustment_quantity=adjustment_data.quantity,
        reason=adjustment_data.reason,
        user_id=current_user.id,
    )

    response = InventoryResponse.model_validate(result).model_dump(mode="json")

    save_idempotency_record(
        db=db,
        key=key,
        user_id=current_user.id,
        endpoint="POST:/api/inventory/adjust",
        response_status=200,
        response_body=response,
    )

    db.commit()

    return result



@router.post(
    "/transfer",
)
def transfer_inventory_api(
    transfer_data: InventoryTransferRequest,
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    key = validate_idempotency_key(idempotency_key)

    existing = get_idempotency_record(
        db=db,
        key=key,
        user_id=current_user.id,
        endpoint="POST:/api/inventory/transfer",
    )

    if existing:
        if existing.response_body:
            return existing.response_body
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Idempotency key is already being processed",
        )

    check_warehouse_access(
        warehouse_id=transfer_data.from_warehouse_id,
        current_user=current_user,
        db=db,
    )

    check_warehouse_access(
        warehouse_id=transfer_data.to_warehouse_id,
        current_user=current_user,
        db=db,
    )

    result = transfer_inventory(
        db=db,
        product_id=transfer_data.product_id,
        from_warehouse_id=transfer_data.from_warehouse_id,
        to_warehouse_id=transfer_data.to_warehouse_id,
        quantity=transfer_data.quantity,
        reason=transfer_data.reason,
        user_id=current_user.id,
    )

    response = {
        "success": True,
        "message": "Inventory transferred successfully",
        "data": result,
    }

    save_idempotency_record(
        db=db,
        key=key,
        user_id=current_user.id,
        endpoint="POST:/api/inventory/transfer",
        response_status=200,
        response_body=response,
    )

    db.commit()

    return response

@router.post(
    "/reserve",
    response_model=InventoryResponse,
)
def reserve_inventory_api(
    reservation_data: InventoryReservationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    inventory = get_inventory_by_id(
        db=db,
        inventory_id=reservation_data.inventory_id,
    )

    if inventory is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inventory not found",
        )

    check_warehouse_access(
        warehouse_id=inventory.warehouse_id,
        current_user=current_user,
        db=db,
    )

    return reserve_inventory(
        db=db,
        inventory_id=reservation_data.inventory_id,
        quantity=reservation_data.quantity,
        user_id=current_user.id,
        reference_id=reservation_data.reference_id,
    )


@router.post(
    "/release",
    response_model=InventoryResponse,
)
def release_inventory_api(
    release_data: InventoryReleaseRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    inventory = get_inventory_by_id(
        db=db,
        inventory_id=release_data.inventory_id,
    )

    if inventory is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inventory not found",
        )

    check_warehouse_access(
        warehouse_id=inventory.warehouse_id,
        current_user=current_user,
        db=db,
    )

    return release_inventory(
        db=db,
        inventory_id=release_data.inventory_id,
        quantity=release_data.quantity,
        user_id=current_user.id,
        reference_id=release_data.reference_id,
    )


@router.get(
    "/low-stock",
    response_model=list[InventoryResponse],
)
def get_low_stock_inventory(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Inventory)

    role_name = (
        current_user.role.name.lower()
        if current_user.role
        else ""
    )

    if role_name != "admin":
        warehouse_ids = (
            db.query(WarehouseUser.warehouse_id)
            .filter(
                WarehouseUser.user_id == current_user.id
            )
            .subquery()
        )

        query = query.filter(
            Inventory.warehouse_id.in_(warehouse_ids)
        )

    available_quantity = (
        Inventory.quantity
        - Inventory.reserved_quantity
    )

    return (
        query
        .filter(
            available_quantity <= Inventory.reorder_level
        )
        .order_by(Inventory.id.desc())
        .all()
    )


@router.get(
    "/{inventory_id}",
    response_model=InventoryResponse,
)
def get_inventory_by_id_api(
    inventory_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    inventory = get_inventory_by_id(
        db=db,
        inventory_id=inventory_id,
    )

    if inventory is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inventory not found",
        )

    check_warehouse_access(
        warehouse_id=inventory.warehouse_id,
        current_user=current_user,
        db=db,
    )

    return inventory


@router.put(
    "/{inventory_id}",
    response_model=InventoryResponse,
)
def update_inventory_api(
    inventory_id: int,
    inventory_data: InventoryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    inventory = get_inventory_by_id(
        db=db,
        inventory_id=inventory_id,
    )

    if inventory is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inventory not found",
        )

    check_warehouse_access(
        warehouse_id=inventory.warehouse_id,
        current_user=current_user,
        db=db,
    )

    return update_existing_inventory(
        db=db,
        inventory_id=inventory_id,
        quantity=inventory_data.quantity,
        reserved_quantity=inventory_data.reserved_quantity,
        reorder_level=inventory_data.reorder_level,
    )