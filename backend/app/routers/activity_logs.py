from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, Query, status, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, get_current_active_user
from app.models.user import User
from app.models.log import TabSwitchLog
from app.models.attempt import ExamAttempt
from app.schemas.activity_log import ActivityLogResponse, PaginatedActivityLogResponse
from app.services import activity_log_service

router = APIRouter(
    tags=["Activity Logs"],
)


# ─────────────────────────────────────────────────────────────────────────────
# POST /activity/log  — proctoring event ingestion (called by student frontend)
# ─────────────────────────────────────────────────────────────────────────────

class ProctoringEventRequest(BaseModel):
    attempt_id: int
    event_type: str           # 'tab_switch' | 'window_blur' | 'page_refresh' | 'fullscreen_exit'
    description: Optional[str] = None
    metadata: Optional[dict] = None


# Valid event_type values accepted by the tab_switch_logs DB constraint
_VALID_TAB_EVENT_TYPES = {"tab_switch", "window_blur", "page_refresh"}

# Map frontend event types that are not in the DB constraint to the nearest valid one
_EVENT_TYPE_MAP = {
    "fullscreen_exit": "window_blur",   # closest semantic match
    "tab_switch": "tab_switch",
    "window_blur": "window_blur",
    "page_refresh": "page_refresh",
}


@router.post(
    "/activity/log",
    status_code=status.HTTP_201_CREATED,
    summary="Record a proctoring/security event for an exam attempt",
    description=(
        "Called by the student proctoring hook to log tab switches, window blurs, "
        "and page refreshes into tab_switch_logs. "
        "Validates that the attempt belongs to the authenticated student."
    ),
)
def log_proctoring_event(
    payload: ProctoringEventRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    # Resolve and validate the attempt
    attempt = db.query(ExamAttempt).filter(ExamAttempt.id == payload.attempt_id).first()
    if not attempt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Exam attempt not found",
        )

    # Only the owning student may log events for their own attempt
    if attempt.student_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to log events for this attempt",
        )

    # Map frontend event type to a DB-valid event_type
    raw_type = (payload.event_type or "").lower().strip()
    db_event_type = _EVENT_TYPE_MAP.get(raw_type)
    if db_event_type is None:
        # Unknown types: silently ignore (don't 422) — just treat as window_blur
        db_event_type = "window_blur"

    # Write to tab_switch_logs
    log_entry = TabSwitchLog(
        attempt_id=attempt.id,
        event_type=db_event_type,
    )
    db.add(log_entry)

    try:
        db.commit()
        db.refresh(log_entry)
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to record proctoring event",
        )

    return {
        "id": log_entry.id,
        "attempt_id": log_entry.attempt_id,
        "event_type": log_entry.event_type,
        "occurred_at": log_entry.occurred_at,
    }




@router.get(
    "/activity-logs",
    response_model=PaginatedActivityLogResponse,
    status_code=status.HTTP_200_OK,
    summary="Query paginated activity audit logs",
    description=(
        "Retrieve auditable activity logs with role-based access control. "
        "Admins have full visibility; examiners can view examination & student logs; "
        "students can only view their own activity logs."
    ),
)
def list_activity_logs(
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    action: Optional[str] = Query(None, description="Filter by action / action_type"),
    entity_type: Optional[str] = Query(None, description="Filter by entity type (e.g. exam, user)"),
    entity_id: Optional[str] = Query(None, description="Filter by entity identifier"),
    start_date: Optional[datetime] = Query(None, description="Filter logs on or after timestamp"),
    end_date: Optional[datetime] = Query(None, description="Filter logs on or before timestamp"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Number of records per page"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return activity_log_service.get_activity_logs(
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


@router.get(
    "/activity-logs/{id}",
    response_model=ActivityLogResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve a specific activity log entry by ID",
    description="Retrieve a single activity log record if authorized under RBAC rules.",
)
def get_activity_log(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return activity_log_service.get_activity_log_by_id(
        db=db,
        log_id=id,
        current_user=current_user,
    )


@router.get(
    "/users/{user_id}/activity-logs",
    response_model=PaginatedActivityLogResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve activity logs for a specific user",
    description=(
        "Retrieve logs associated with the specified user. "
        "Students are only permitted to query their own ID."
    ),
)
def get_user_logs(
    user_id: int,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return activity_log_service.get_user_activity_logs(
        db=db,
        target_user_id=user_id,
        current_user=current_user,
        page=page,
        page_size=page_size,
    )
