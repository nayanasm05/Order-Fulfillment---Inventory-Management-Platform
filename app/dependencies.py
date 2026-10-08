from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.security import decode_token
from app.database import get_db
from app.models import User, WarehouseUser


bearer_scheme = HTTPBearer()


# ============================================================
# CURRENT USER
# ============================================================

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired authentication token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token = credentials.credentials

    try:
        payload = decode_token(token)

        if payload.get("type") != "access":
            raise credentials_exception

        user_id = payload.get("sub")

        if user_id is None:
            raise credentials_exception

    except (JWTError, ValueError):
        raise credentials_exception

    user = db.query(User).filter(
        User.id == int(user_id)
    ).first()

    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )

    return user


# ============================================================
# ROLE CHECK
# ============================================================

def require_role(*allowed_roles):
    def role_checker(
        current_user: User = Depends(get_current_user),
    ):
        if current_user.role is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User role is not assigned",
            )

        if current_user.role.name not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to perform this action",
            )

        return current_user

    return role_checker


# ============================================================
# WAREHOUSE ACCESS CHECK
# ============================================================

def check_warehouse_access(
    warehouse_id: int,
    current_user: User,
    db: Session,
):
    # Admin can access every warehouse
    if (
        current_user.role
        and current_user.role.name.lower() == "admin"
    ):
        return True

    # Check assigned warehouse
    warehouse_access = (
        db.query(WarehouseUser)
        .filter(
            WarehouseUser.user_id == current_user.id,
            WarehouseUser.warehouse_id == warehouse_id,
        )
        .first()
    )

    if warehouse_access is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to access this warehouse",
        )

    return True


# ============================================================
# REQUIRE WAREHOUSE ACCESS
# ============================================================

def require_warehouse_access(
    warehouse_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    check_warehouse_access(
        warehouse_id=warehouse_id,
        current_user=current_user,
        db=db,
    )

    return current_user