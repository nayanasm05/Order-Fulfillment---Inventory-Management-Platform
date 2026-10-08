from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy import asc, desc, func
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import check_warehouse_access, get_current_user
from app.models import Order, User, WarehouseUser
from app.schemas import (
    OrderCancellationRequest,
    OrderCreate,
    OrderListPaginatedResponse,
    OrderResponse,
    OrderStatusHistoryResponse,
    OrderStatusUpdate,
)
from app.services.order_service import (
    cancel_existing_order,
    create_new_order,
    get_customer_orders,
    get_order,
    get_orders,
    get_warehouse_orders,
    update_order_status,
)
from app.services.idempotency_service import (
    get_idempotency_record,
    validate_idempotency_key,
    save_idempotency_record,
)

router = APIRouter(
    prefix="/api/orders",
    tags=["Orders"],
)


@router.post(
    "",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
)
@router.post(
    "",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_order_api(
    order_data: OrderCreate,
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    key = validate_idempotency_key(idempotency_key)

    existing = get_idempotency_record(
        db=db,
        key=key,
        user_id=current_user.id,
        endpoint="POST:/api/orders",
    )

    if existing:
        if existing.response_body:
            return existing.response_body
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Idempotency key is already being processed",
        )

    check_warehouse_access(
        warehouse_id=order_data.warehouse_id,
        current_user=current_user,
        db=db,
    )

    order = create_new_order(
        db=db,
        customer_id=current_user.id,
        order_data=order_data,
    )

    response = OrderResponse.model_validate(order).model_dump(mode="json")

    save_idempotency_record(
        db=db,
        key=key,
        user_id=current_user.id,
        endpoint="POST:/api/orders",
        response_status=201,
        response_body=response,
    )

    db.commit()

    return order

@router.get(
    "",
    response_model=OrderListPaginatedResponse,
)
def list_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: str | None = Query(None, alias="status"),
    customer_id: int | None = Query(None, ge=1),
    warehouse_id: int | None = Query(None, ge=1),
    payment_status: str | None = Query(None),
    start_date: str | None = Query(None),
    end_date: str | None = Query(None),
    min_total: float | None = Query(None, ge=0),
    max_total: float | None = Query(None, ge=0),
    sort_by: str = Query(
        "created_at",
        pattern="^(created_at|updated_at|total_amount|status)$",
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

    query = db.query(Order)

    if role_name == "customer":
        query = query.filter(
            Order.customer_id == current_user.id
        )

        if customer_id is not None:
            if customer_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You can only access your own orders",
                )

    elif role_name == "admin":
        if customer_id is not None:
            query = query.filter(
                Order.customer_id == customer_id
            )

    else:
        warehouse_query = db.query(
            WarehouseUser.warehouse_id
        ).filter(
            WarehouseUser.user_id == current_user.id
        )

        assigned_warehouse_ids = [
            item[0]
            for item in warehouse_query.all()
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
                Order.warehouse_id == warehouse_id
            )
        else:
            query = query.filter(
                Order.warehouse_id.in_(assigned_warehouse_ids)
            )

        if customer_id is not None:
            query = query.filter(
                Order.customer_id == customer_id
            )

    if role_name == "customer" and warehouse_id is not None:
        query = query.filter(
            Order.warehouse_id == warehouse_id
        )

    if status_filter is not None:
        query = query.filter(
            func.lower(Order.status) == status_filter.lower()
        )

    if payment_status is not None:
        query = query.filter(
            func.lower(Order.payment_status)
            == payment_status.lower()
        )

    if start_date is not None:
        query = query.filter(
            Order.created_at >= start_date
        )

    if end_date is not None:
        query = query.filter(
            Order.created_at <= end_date
        )

    if min_total is not None:
        query = query.filter(
            Order.total_amount >= min_total
        )

    if max_total is not None:
        query = query.filter(
            Order.total_amount <= max_total
        )

    sort_column_map = {
        "created_at": Order.created_at,
        "updated_at": Order.updated_at,
        "total_amount": Order.total_amount,
        "status": Order.status,
    }

    sort_column = sort_column_map[sort_by]

    if sort_order == "asc":
        query = query.order_by(asc(sort_column))
    else:
        query = query.order_by(desc(sort_column))

    total = query.count()

    offset = (page - 1) * page_size

    orders = (
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
        "items": orders,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": total_pages,
        },
    }


@router.get(
    "/{order_id}",
    response_model=OrderResponse,
)
def get_order_api(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    order = get_order(
        db=db,
        order_id=order_id,
    )

    role_name = (
        current_user.role.name.lower()
        if current_user.role
        else ""
    )

    if role_name == "customer":
        if order.customer_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to access this order",
            )

        return order

    if role_name == "admin":
        return order

    check_warehouse_access(
        warehouse_id=order.warehouse_id,
        current_user=current_user,
        db=db,
    )

    return order


@router.patch(
    "/{order_id}/status",
    response_model=OrderResponse,
)
def update_order_status_api(
    order_id: int,
    status_data: OrderStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    order = get_order(
        db=db,
        order_id=order_id,
    )

    role_name = (
        current_user.role.name.lower()
        if current_user.role
        else ""
    )

    if role_name == "customer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Customers cannot change order status",
        )

    if role_name != "admin":
        check_warehouse_access(
            warehouse_id=order.warehouse_id,
            current_user=current_user,
            db=db,
        )

    return update_order_status(
        db=db,
        order_id=order_id,
        new_status=status_data.status,
        changed_by=current_user.id,
        reason=status_data.reason,
    )


@router.post(
    "/{order_id}/cancel",
    response_model=OrderResponse,
)
def cancel_order_api(
    order_id: int,
    cancellation_data: OrderCancellationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    order = get_order(
        db=db,
        order_id=order_id,
    )

    role_name = (
        current_user.role.name.lower()
        if current_user.role
        else ""
    )

    if role_name == "customer":
        if order.customer_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only cancel your own orders",
            )

    elif role_name == "admin":
        pass

    else:
        check_warehouse_access(
            warehouse_id=order.warehouse_id,
            current_user=current_user,
            db=db,
        )

    return cancel_existing_order(
        db=db,
        order_id=order_id,
        cancelled_by=current_user.id,
        reason=cancellation_data.reason,
    )


@router.get(
    "/{order_id}/history",
    response_model=list[OrderStatusHistoryResponse],
)
def get_order_history_api(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    order = get_order(
        db=db,
        order_id=order_id,
    )

    role_name = (
        current_user.role.name.lower()
        if current_user.role
        else ""
    )

    if role_name == "customer":
        if order.customer_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to access this order",
            )

    elif role_name == "admin":
        pass

    else:
        check_warehouse_access(
            warehouse_id=order.warehouse_id,
            current_user=current_user,
            db=db,
        )

    from app.repositories.order_repository import (
        get_order_status_history,
    )

    return get_order_status_history(
        db=db,
        order_id=order_id,
    )