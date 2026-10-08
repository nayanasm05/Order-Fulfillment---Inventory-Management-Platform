from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.services.dashboard_service import (
    get_admin_dashboard,
    get_customer_dashboard,
    get_dashboard_summary,
    get_role_name,
    get_warehouse_manager_dashboard,
)

router = APIRouter(
    prefix="/api/dashboard",
    tags=["Dashboard"],
)


@router.get("/summary")
def dashboard_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_dashboard_summary(
        db=db,
        current_user=current_user,
    )


@router.get("/admin")
def admin_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    role = get_role_name(current_user)

    if role != "admin":
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin dashboard access denied",
        )

    return {
        "role": "Admin",
        "dashboard": get_admin_dashboard(db),
    }


@router.get("/warehouse")
def warehouse_manager_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    role = get_role_name(current_user)

    if role != "warehouse manager":
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Warehouse Manager dashboard access denied",
        )

    return {
        "role": "Warehouse Manager",
        "dashboard": get_warehouse_manager_dashboard(
            db=db,
            user_id=current_user.id,
        ),
    }


@router.get("/customer")
def customer_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    role = get_role_name(current_user)

    if role != "customer":
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Customer dashboard access denied",
        )

    return {
        "role": "Customer",
        "dashboard": get_customer_dashboard(
            db=db,
            customer_id=current_user.id,
        ),
    }