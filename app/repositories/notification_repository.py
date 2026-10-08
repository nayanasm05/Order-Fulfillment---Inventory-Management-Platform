from datetime import datetime

from sqlalchemy.orm import Session

from app.models import Notification


def create_notification(
    db: Session,
    notification: Notification,
):
    db.add(notification)
    db.flush()
    return notification


def get_notification_by_id(
    db: Session,
    notification_id: int,
):
    return (
        db.query(Notification)
        .filter(Notification.id == notification_id)
        .first()
    )


def get_user_notifications(
    db: Session,
    user_id: int,
):
    return (
        db.query(Notification)
        .filter(Notification.user_id == user_id)
        .order_by(Notification.created_at.desc())
        .all()
    )


def get_unread_notifications(
    db: Session,
    user_id: int,
):
    return (
        db.query(Notification)
        .filter(
            Notification.user_id == user_id,
            Notification.is_read.is_(False),
        )
        .order_by(Notification.created_at.desc())
        .all()
    )


def mark_as_read(
    notification: Notification,
):
    notification.is_read = True
    notification.read_at = datetime.utcnow()


def mark_all_as_read(
    db: Session,
    user_id: int,
):
    notifications = (
        db.query(Notification)
        .filter(
            Notification.user_id == user_id,
            Notification.is_read.is_(False),
        )
        .all()
    )

    for notification in notifications:
        mark_as_read(notification)

    return notifications