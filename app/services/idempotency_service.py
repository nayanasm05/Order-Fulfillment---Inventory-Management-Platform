from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models import IdempotencyKey

def get_idempotency_record(db: Session, key: str, user_id: int, endpoint: str):
    record = (
        db.query(IdempotencyKey)
        .filter(
            IdempotencyKey.key == key,
            IdempotencyKey.user_id == user_id,
            IdempotencyKey.endpoint == endpoint,
        )
        .first()
    )
    return record

def validate_idempotency_key(key: str | None):
    if not key or not key.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Idempotency-Key header is required",
        )
    return key.strip()

def save_idempotency_record(
    db: Session,
    key: str,
    user_id: int,
    endpoint: str,
    response_status: int,
    response_body: dict,
):
    record = IdempotencyKey(
        key=key,
        user_id=user_id,
        endpoint=endpoint,
        response_status=response_status,
        response_body=response_body,
    )
    db.add(record)
    db.flush()
    return record