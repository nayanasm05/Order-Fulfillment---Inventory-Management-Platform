from sqlalchemy.orm import Session

from app.models import Warehouse


def get_warehouse_by_id(db: Session, warehouse_id: int):
    return db.query(Warehouse).filter(Warehouse.id == warehouse_id).first()


def get_warehouse_by_code(db: Session, code: str):
    return db.query(Warehouse).filter(Warehouse.code == code).first()


def get_warehouses(db: Session):
    return db.query(Warehouse).order_by(Warehouse.id.desc()).all()


def create_warehouse(db: Session, warehouse: Warehouse):
    db.add(warehouse)
    db.commit()
    db.refresh(warehouse)
    return warehouse


def update_warehouse(db: Session, warehouse: Warehouse):
    db.commit()
    db.refresh(warehouse)
    return warehouse