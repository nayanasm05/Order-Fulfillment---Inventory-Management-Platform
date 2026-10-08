from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.schemas import (
    RefundProcessRequest,
    RefundResponse,
)
from app.services.refund_service import (
    create_refund_for_return,
    get_refund,
    list_my_refunds,
    process_refund,
)


router = APIRouter(
    prefix="/api/refunds",
    tags=["Refunds"],
)


@router.post(
    "/return/{return_request_id}",
    response_model=RefundResponse,
)
def create_refund(
    return_request_id: int,
    request: RefundProcessRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return create_refund_for_return(
        db,
        return_request_id,
        current_user,
        request.reason,
    )


@router.get(
    "/my",
    response_model=list[RefundResponse],
)
def get_my_refunds(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return list_my_refunds(
        db,
        current_user,
    )


@router.get(
    "/{refund_id}",
    response_model=RefundResponse,
)
def get_refund_details(
    refund_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_refund(
        db,
        refund_id,
        current_user,
    )


@router.patch(
    "/{refund_id}/process",
    response_model=RefundResponse,
)
def process_refund_api(
    refund_id: int,
    request: RefundProcessRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return process_refund(
        db,
        refund_id,
        current_user,
        request.reason,
    )