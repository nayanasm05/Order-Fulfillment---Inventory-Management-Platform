from datetime import datetime

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.schemas import AuditLogListResponse
from app.services.audit_service import list_audit_logs

router = APIRouter(
    prefix="/api/audit-logs",
    tags=["Audit Logs"],
)


@router.get(
    "",
    response_model=AuditLogListResponse,
)
def get_audit_logs_api(
    request: Request,
    user_id: int | None = Query(
        default=None,
        gt=0,
    ),
    action: str | None = None,
    entity_type: str | None = None,
    entity_id: int | None = Query(
        default=None,
        gt=0,
    ),
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    page: int = Query(
        default=1,
        ge=1,
    ),
    page_size: int = Query(
        default=20,
        ge=1,
        le=100,
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    logs, total = list_audit_logs(
        db=db,
        current_user=current_user,
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        start_date=start_date,
        end_date=end_date,
        page=page,
        page_size=page_size,
    )

    total_pages = (
        (total + page_size - 1) // page_size
        if total
        else 0
    )

    return {
        "items": logs,
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": total_pages,
    }