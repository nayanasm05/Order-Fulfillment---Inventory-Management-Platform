from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.schemas import OrderResponse
from app.services.fulfillment_service import (
    confirm_order,
    deliver_order,
    pack_order,
    ship_order,
    start_processing,
)


router = APIRouter(
    prefix="/api/orders",
    tags=["Fulfillment Workflow"],
)


@router.patch(
    "/{order_id}/fulfillment/confirm",
    response_model=OrderResponse,
)
def confirm_order_api(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return confirm_order(db, order_id, current_user)


@router.patch(
    "/{order_id}/fulfillment/process",
    response_model=OrderResponse,
)
def start_processing_api(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return start_processing(db, order_id, current_user)


@router.patch(
    "/{order_id}/fulfillment/pack",
    response_model=OrderResponse,
)
def pack_order_api(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return pack_order(db, order_id, current_user)


@router.patch(
    "/{order_id}/fulfillment/ship",
    response_model=OrderResponse,
)
def ship_order_api(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return ship_order(db, order_id, current_user)


@router.patch(
    "/{order_id}/fulfillment/deliver",
    response_model=OrderResponse,
)
def deliver_order_api(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return deliver_order(db, order_id, current_user)