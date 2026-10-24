from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, require_role
from app.models.user import User
from app.schemas.security_monitoring import SecurityEventResponse, PaginatedSecurityEventsResponse
from app.services import security_monitoring

router = APIRouter(
    prefix="/security",
    tags=["Security Monitoring"],
    dependencies=[Depends(require_role(["admin"]))],
)


@router.get(
    "/events",
    response_model=PaginatedSecurityEventsResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve paginated security monitoring events",
    description="Query auditable security events, access violations, and suspicious exam activities. Restricted strictly to administrators.",
)
def list_security_events(
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    event_type: Optional[str] = Query(None, description="Filter by security event type"),
    severity: Optional[str] = Query(None, description="Filter by severity level (LOW, MEDIUM, HIGH, CRITICAL)"),
    entity_type: Optional[str] = Query(None, description="Filter by entity type"),
    entity_id: Optional[str] = Query(None, description="Filter by entity ID"),
    start_date: Optional[datetime] = Query(None, description="Filter events on or after timestamp"),
    end_date: Optional[datetime] = Query(None, description="Filter events on or before timestamp"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Records per page"),
    db: Session = Depends(get_db),
):
    return security_monitoring.get_security_events(
        db=db,
        user_id=user_id,
        event_type=event_type,
        severity=severity,
        entity_type=entity_type,
        entity_id=entity_id,
        start_date=start_date,
        end_date=end_date,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/events/{event_id}",
    response_model=SecurityEventResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve details of a specific security event",
    description="Retrieve a single security event record by its primary key ID.",
)
def get_single_security_event(
    event_id: int,
    db: Session = Depends(get_db),
):
    return security_monitoring.get_security_event_by_id(
        db=db,
        event_id=event_id,
    )
