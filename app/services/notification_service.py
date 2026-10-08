from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import Notification, User
from app.repositories.notification_repository import (
    create_notification,
    get_notification_by_id,
    get_unread_notifications,
    get_user_notifications,
    mark_all_as_read,
    mark_as_read,
)


def create_user_notification(
    db: Session,
    user_id: int,
    title: str,
    message: str,
    notification_type: str,
    reference_type: str | None = None,
    reference_id: int | None = None,
):
    user = (
        db.query(User)
        .filter(User.id == user_id)
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    notification = Notification(
        user_id=user_id,
        title=title,
        message=message,
        notification_type=notification_type,
        reference_type=reference_type,
        reference_id=reference_id,
        is_read=False,
    )

    create_notification(db, notification)

    db.commit()
    db.refresh(notification)

    return notification


def get_my_notifications(
    db: Session,
    current_user: User,
):
    return get_user_notifications(
        db,
        current_user.id,
    )


def get_my_unread_notifications(
    db: Session,
    current_user: User,
):
    return get_unread_notifications(
        db,
        current_user.id,
    )


def get_notification(
    db: Session,
    notification_id: int,
    current_user: User,
):
    notification = get_notification_by_id(
        db,
        notification_id,
    )

    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )

    if notification.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only access your own notifications",
        )

    return notification


def mark_notification_as_read(
    db: Session,
    notification_id: int,
    current_user: User,
):
    notification = get_notification(
        db,
        notification_id,
        current_user,
    )

    if notification.is_read:
        return notification

    mark_as_read(notification)

    db.commit()
    db.refresh(notification)

    return notification


def mark_my_notifications_as_read(
    db: Session,
    current_user: User,
):
    notifications = mark_all_as_read(
        db,
        current_user.id,
    )

    db.commit()

    for notification in notifications:
        db.refresh(notification)

    return notifications