from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.database import get_db
from app.dependencies import get_current_user
from app.models import RefreshToken, Role, User
from app.schemas import (
    RefreshTokenRequest,
    TokenResponse,
    UserLogin,
    UserRegister,
    UserResponse,
)


router = APIRouter(
    prefix="/api/auth",
    tags=["Authentication"],
)


# ============================================================
# CHANGE PASSWORD SCHEMA
# ============================================================

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


# ============================================================
# REGISTER
# ============================================================

@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(
    user_data: UserRegister,
    db: Session = Depends(get_db),
):
    existing_user = db.query(User).filter(
        (User.username == user_data.username)
        | (User.email == user_data.email)
    ).first()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username or email already exists",
        )

    role = db.query(Role).filter(
        Role.id == user_data.role_id
    ).first()

    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found",
        )

    user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hash_password(user_data.password),
        role_id=user_data.role_id,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


# ============================================================
# LOGIN
# ============================================================

@router.post(
    "/login",
    response_model=TokenResponse,
)
def login(
    login_data: UserLogin,
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(
        User.username == login_data.username
    ).first()

    if not user or not verify_password(
        login_data.password,
        user.hashed_password,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Inactive users cannot login
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )

    # Create access token
    access_token = create_access_token(
        {
            "sub": str(user.id),
            "role_id": user.role_id,
        }
    )

    # Create refresh token
    refresh_token = create_refresh_token(
        {
            "sub": str(user.id),
        }
    )

    # Store refresh token in database
    refresh_token_record = RefreshToken(
        user_id=user.id,
        token=refresh_token,
        is_revoked=False,
        expires_at=datetime.utcnow() + timedelta(days=7),
    )

    db.add(refresh_token_record)
    db.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
    )


# ============================================================
# GET CURRENT USER
# ============================================================

@router.get(
    "/me",
    response_model=UserResponse,
)
def get_me(
    current_user: User = Depends(get_current_user),
):
    return current_user


# ============================================================
# REFRESH TOKEN - ROTATION
# ============================================================

@router.post(
    "/refresh",
    response_model=TokenResponse,
)
def refresh_token(
    token_data: RefreshTokenRequest,
    db: Session = Depends(get_db),
):
    # --------------------------------------------------------
    # Decode refresh token
    # --------------------------------------------------------

    try:
        payload = decode_token(
            token_data.refresh_token
        )

        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
            )

        user_id = payload.get("sub")

        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
            )

    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    # --------------------------------------------------------
    # Find refresh token in database
    # --------------------------------------------------------

    stored_token = db.query(RefreshToken).filter(
        RefreshToken.token == token_data.refresh_token
    ).first()

    if not stored_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token not found",
        )

    # --------------------------------------------------------
    # Check whether token is revoked
    # --------------------------------------------------------

    if stored_token.is_revoked:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has been revoked",
        )

    # --------------------------------------------------------
    # Check token expiration
    # --------------------------------------------------------

    if stored_token.expires_at < datetime.utcnow():
        stored_token.is_revoked = True
        db.commit()

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has expired",
        )

    # --------------------------------------------------------
    # Get user
    # --------------------------------------------------------

    user = db.query(User).filter(
        User.id == int(user_id)
    ).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User is inactive",
        )

    # --------------------------------------------------------
    # Revoke OLD refresh token
    # --------------------------------------------------------

    stored_token.is_revoked = True

    # --------------------------------------------------------
    # Create NEW tokens
    # --------------------------------------------------------

    new_access_token = create_access_token(
        {
            "sub": str(user.id),
            "role_id": user.role_id,
        }
    )

    new_refresh_token = create_refresh_token(
        {
            "sub": str(user.id),
        }
    )

    # --------------------------------------------------------
    # Store NEW refresh token
    # --------------------------------------------------------

    new_refresh_record = RefreshToken(
        user_id=user.id,
        token=new_refresh_token,
        is_revoked=False,
        expires_at=datetime.utcnow() + timedelta(days=7),
    )

    db.add(new_refresh_record)
    db.commit()

    return TokenResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
    )


# ============================================================
# LOGOUT
# ============================================================

@router.post("/logout")
def logout(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Revoke all active refresh tokens for the user
    db.query(RefreshToken).filter(
        RefreshToken.user_id == current_user.id,
        RefreshToken.is_revoked == False,
    ).update(
        {
            "is_revoked": True
        }
    )

    db.commit()

    return {
        "message": "Successfully logged out"
    }


# ============================================================
# CHANGE PASSWORD
# ============================================================

@router.post("/change-password")
def change_password(
    password_data: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # --------------------------------------------------------
    # Verify current password
    # --------------------------------------------------------

    if not verify_password(
        password_data.current_password,
        current_user.hashed_password,
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    # --------------------------------------------------------
    # Prevent same password
    # --------------------------------------------------------

    if verify_password(
        password_data.new_password,
        current_user.hashed_password,
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from current password",
        )

    # --------------------------------------------------------
    # Update password
    # --------------------------------------------------------

    current_user.hashed_password = hash_password(
        password_data.new_password
    )

    # --------------------------------------------------------
    # Revoke existing refresh tokens
    # --------------------------------------------------------

    db.query(RefreshToken).filter(
        RefreshToken.user_id == current_user.id,
        RefreshToken.is_revoked == False,
    ).update(
        {
            "is_revoked": True
        }
    )

    db.commit()

    return {
        "message": "Password changed successfully"
    }