from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import Warehouse
from app.repositories.warehouse_repository import (
    create_warehouse,
    get_warehouse_by_code,
    get_warehouse_by_id,
    update_warehouse,
)


def create_new_warehouse(
    db: Session,
    name: str,
    code: str,
    location: str | None,
):
    existing_warehouse = get_warehouse_by_code(db, code)

    if existing_warehouse:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Warehouse code already exists",
        )

    warehouse = Warehouse(
        name=name,
        code=code,
        location=location,
    )

    return create_warehouse(db, warehouse)


def get_warehouse(db: Session, warehouse_id: int):
    warehouse = get_warehouse_by_id(db, warehouse_id)

    if not warehouse:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Warehouse not found",
        )

    return warehouse


def update_existing_warehouse(
    db: Session,
    warehouse_id: int,
    name: str | None = None,
    location: str | None = None,
    is_active: bool | None = None,
):
    warehouse = get_warehouse_by_id(db, warehouse_id)

    if not warehouse:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Warehouse not found",
        )

    if name is not None:
        warehouse.name = name

    if location is not None:
        warehouse.location = location

    if is_active is not None:
        warehouse.is_active = is_active

    return update_warehouse(db, warehouse)