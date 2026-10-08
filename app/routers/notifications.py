from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.schemas import (
    NotificationCreate,
    NotificationResponse,
)
from app.services.notification_service import (
    create_user_notification,
    get_my_notifications,
    get_my_unread_notifications,
    get_notification,
    mark_my_notifications_as_read,
    mark_notification_as_read,
)


router = APIRouter(
    prefix="/api/notifications",
    tags=["Notifications"],
)


@router.post(
    "",
    response_model=NotificationResponse,
)
def create_notification_api(
    request: NotificationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role.name != "Admin":
        from fastapi import HTTPException

        raise HTTPException(
            status_code=403,
            detail="Only Admin can create notifications",
        )

    return create_user_notification(
        db,
        request.user_id,
        request.title,
        request.message,
        request.notification_type,
        request.reference_type,
        request.reference_id,
    )


@router.get(
    "/my",
    response_model=list[NotificationResponse],
)
def get_my_notifications_api(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_my_notifications(
        db,
        current_user,
    )


@router.get(
    "/my/unread",
    response_model=list[NotificationResponse],
)
def get_my_unread_notifications_api(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_my_unread_notifications(
        db,
        current_user,
    )


@router.get(
    "/{notification_id}",
    response_model=NotificationResponse,
)
def get_notification_api(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_notification(
        db,
        notification_id,
        current_user,
    )


@router.patch(
    "/{notification_id}/read",
    response_model=NotificationResponse,
)
def mark_notification_read_api(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return mark_notification_as_read(
        db,
        notification_id,
        current_user,
    )


@router.patch(
    "/my/read-all",
    response_model=list[NotificationResponse],
)
def mark_all_notifications_read_api(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return mark_my_notifications_as_read(
        db,
        current_user,
    )