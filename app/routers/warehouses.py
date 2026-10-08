from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, check_warehouse_access
from app.models import User, Warehouse
from app.repositories.warehouse_repository import get_warehouses
from app.schemas import (
    WarehouseCreate,
    WarehouseResponse,
    WarehouseUpdate,
)
from app.services.warehouse_service import (
    create_new_warehouse,
    get_warehouse,
    update_existing_warehouse,
)


router = APIRouter(
    prefix="/api/warehouses",
    tags=["Warehouses"],
)


# ============================================================
# CREATE WAREHOUSE
# ============================================================

@router.post(
    "",
    response_model=WarehouseResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_warehouse(
    warehouse_data: WarehouseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Only Admin can create warehouses
    if (
        current_user.role is None
        or current_user.role.name.lower() != "admin"
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Admin can create warehouses",
        )

    return create_new_warehouse(
        db=db,
        name=warehouse_data.name,
        code=warehouse_data.code,
        location=warehouse_data.location,
    )


# ============================================================
# LIST WAREHOUSES
# ============================================================

@router.get(
    "",
    response_model=list[WarehouseResponse],
)
def list_warehouses(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Admin can see all warehouses
    if (
        current_user.role
        and current_user.role.name.lower() == "admin"
    ):
        return get_warehouses(db)

    # Other users only see warehouses assigned to them
    warehouses = (
        db.query(Warehouse)
        .join(Warehouse.users)
        .filter(
            Warehouse.users.any(
                user_id=current_user.id
            )
        )
        .order_by(Warehouse.id.desc())
        .all()
    )

    return warehouses


# ============================================================
# GET WAREHOUSE BY ID
# ============================================================

@router.get(
    "/{warehouse_id}",
    response_model=WarehouseResponse,
)
def get_warehouse_by_id(
    warehouse_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    check_warehouse_access(
        warehouse_id=warehouse_id,
        current_user=current_user,
        db=db,
    )

    return get_warehouse(
        db=db,
        warehouse_id=warehouse_id,
    )


# ============================================================
# UPDATE WAREHOUSE
# ============================================================

@router.put(
    "/{warehouse_id}",
    response_model=WarehouseResponse,
)
def update_warehouse(
    warehouse_id: int,
    warehouse_data: WarehouseUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Only Admin can update warehouse master data
    if (
        current_user.role is None
        or current_user.role.name.lower() != "admin"
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Admin can update warehouses",
        )

    return update_existing_warehouse(
        db=db,
        warehouse_id=warehouse_id,
        name=warehouse_data.name,
        location=warehouse_data.location,
        is_active=warehouse_data.is_active,
    )


# ============================================================
# DEACTIVATE WAREHOUSE
# ============================================================

@router.delete(
    "/{warehouse_id}",
    response_model=WarehouseResponse,
)
def deactivate_warehouse(
    warehouse_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Only Admin can deactivate warehouses
    if (
        current_user.role is None
        or current_user.role.name.lower() != "admin"
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Admin can deactivate warehouses",
        )

    warehouse = get_warehouse(
        db=db,
        warehouse_id=warehouse_id,
    )

    if warehouse is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Warehouse not found",
        )

    warehouse.is_active = False

    db.commit()
    db.refresh(warehouse)

    return warehouse


# ============================================================
# ACTIVATE WAREHOUSE
# ============================================================

@router.patch(
    "/{warehouse_id}/activate",
)
def activate_warehouse(
    warehouse_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Only Admin can activate warehouses
    if (
        current_user.role is None
        or current_user.role.name.lower() != "admin"
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Admin can activate warehouses",
        )

    warehouse = db.query(Warehouse).filter(
        Warehouse.id == warehouse_id
    ).first()

    if not warehouse:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Warehouse not found",
        )

    if warehouse.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Warehouse is already active",
        )

    warehouse.is_active = True

    db.commit()
    db.refresh(warehouse)

    return {
        "message": "Warehouse activated successfully",
        "warehouse_id": warehouse.id,
        "is_active": warehouse.is_active,
    }