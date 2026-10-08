from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.schemas import (
    ReturnRequestCreate,
    ReturnRequestResponse,
    ReturnStatusUpdate,
)
from app.services.return_service import (
    create_return_request,
    get_return,
    list_customer_returns,
    list_order_returns,
    update_return_status,
)


router = APIRouter(
    prefix="/api/returns",
    tags=["Returns Management"],
)


@router.post(
    "",
    response_model=ReturnRequestResponse,
)
def create_return_api(
    data: ReturnRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return create_return_request(
        db=db,
        order_item_id=data.order_item_id,
        quantity=data.quantity,
        reason=data.reason,
        current_user=current_user,
    )


@router.get(
    "/my",
    response_model=list[ReturnRequestResponse],
)
def get_my_returns_api(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return list_customer_returns(
        db,
        current_user,
    )


@router.get(
    "/order/{order_id}",
    response_model=list[ReturnRequestResponse],
)
def get_order_returns_api(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return list_order_returns(
        db,
        order_id,
        current_user,
    )


@router.get(
    "/{return_id}",
    response_model=ReturnRequestResponse,
)
def get_return_api(
    return_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_return(
        db,
        return_id,
        current_user,
    )


@router.patch(
    "/{return_id}/status",
    response_model=ReturnRequestResponse,
)
def update_return_status_api(
    return_id: int,
    data: ReturnStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return update_return_status(
        db=db,
        return_id=return_id,
        new_status=data.status,
        current_user=current_user,
    )