from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.schemas import (
    OrderAssignmentCreate,
    OrderAssignmentResponse,
    OrderReassignmentRequest,
)
from app.services.order_assignment_service import (
    assign_order,
    get_active_assignment,
    get_assignment_history,
    reassign_order,
)

router = APIRouter(
    prefix="/api/orders",
    tags=["Order Assignment"],
)


@router.post(
    "/{order_id}/assign",
    response_model=OrderAssignmentResponse,
    status_code=status.HTTP_201_CREATED,
)
def assign_order_api(
    order_id: int,
    request: OrderAssignmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if order_id != request.order_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order ID in path and request body must match",
        )

    role = current_user.role.name.lower() if current_user.role else ""

    if role not in {"admin", "warehouse manager"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Admin or Warehouse Manager can assign orders",
        )

    return assign_order(
        db=db,
        order_id=order_id,
        assigned_to=request.assigned_to,
        assigned_by=current_user.id,
        reason=request.reason,
    )


@router.patch(
    "/{order_id}/assign",
    response_model=OrderAssignmentResponse,
)
def reassign_order_api(
    order_id: int,
    request: OrderReassignmentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    role = current_user.role.name.lower() if current_user.role else ""

    if role not in {"admin", "warehouse manager"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Admin or Warehouse Manager can reassign orders",
        )

    return reassign_order(
        db=db,
        order_id=order_id,
        assigned_to=request.assigned_to,
        assigned_by=current_user.id,
        reason=request.reason,
    )


@router.get(
    "/{order_id}/assignment",
    response_model=OrderAssignmentResponse,
)
def get_active_order_assignment(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_active_assignment(
        db=db,
        order_id=order_id,
        current_user=current_user,
    )


@router.get(
    "/{order_id}/assignment/history",
    response_model=list[OrderAssignmentResponse],
)
def get_order_assignment_history(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_assignment_history(
        db=db,
        order_id=order_id,
        current_user=current_user,
    )