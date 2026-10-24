from datetime import datetime, timezone
from typing import Optional, Dict, Any, Union, List
from fastapi import Request, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc

from app.models.log import ActivityLog
from app.models.user import User


SENSITIVE_KEYS = {
    "password", "passwd", "password_hash", "token", "access_token",
    "refresh_token", "secret", "authorization", "api_key", "credentials"
}


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def sanitize_data(data: Any) -> Any:
    """Recursively scrub sensitive keys (passwords, tokens, secrets) from metadata/dictionaries."""
    if isinstance(data, dict):
        sanitized = {}
        for k, v in data.items():
            if str(k).lower() in SENSITIVE_KEYS:
                sanitized[k] = "[REDACTED]"
            elif isinstance(v, (dict, list)):
                sanitized[k] = sanitize_data(v)
            else:
                sanitized[k] = v
        return sanitized
    elif isinstance(data, list):
        return [sanitize_data(item) for item in data]
    return data


def log_activity(
    db: Session,
    action: str,
    user_id: Optional[int] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[Union[str, int]] = None,
    description: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    request: Optional[Request] = None,
    commit: bool = True,
) -> Optional[ActivityLog]:
    """
    Centralized activity logging service function.
    Safely creates an immutable ActivityLog record in the database.
    
    Extracts IP address and User-Agent from Request if provided.
    Scrubs any sensitive credential information from metadata.
    """
    # Extract request metadata if request is available
    if request is not None:
        if not ip_address:
            ip_address = request.client.host if request.client else None
        if not user_agent:
            user_agent = request.headers.get("user-agent")

    # Sanitize metadata to never store passwords or secrets
    clean_metadata = sanitize_data(metadata) if metadata is not None else None

    # Clean description if needed
    clean_description = description

    str_entity_id = str(entity_id) if entity_id is not None else None

    now = utc_now()

    try:
        log_entry = ActivityLog(
            user_id=user_id,
            action_type=action,
            entity_type=entity_type,
            entity_id=str_entity_id,
            description=clean_description,
            metadata_json=clean_metadata,
            ip_address=ip_address,
            user_agent=user_agent,
            occurred_at=now,
            created_at=now,
            updated_at=now,
        )
        db.add(log_entry)
        if commit:
            db.commit()
            db.refresh(log_entry)
        return log_entry
    except Exception:
        if commit:
            db.rollback()
        return None


def _get_user_roles(user: User) -> set[str]:
    """Helper to extract user role names in lowercase."""
    roles = {r.name.lower() for r in user.roles}
    if user.role:
        roles.add(user.role.lower())
    return roles


def get_activity_logs(
    db: Session,
    current_user: User,
    user_id: Optional[int] = None,
    action: Optional[str] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    page: int = 1,
    page_size: int = 20,
) -> Dict[str, Any]:
    """
    Retrieve paginated activity logs with role-based filtering.
    - Students are strictly restricted to their own logs.
    - Examiners can access examination-related logs and assigned students.
    - Admins have full access.
    """
    user_roles = _get_user_roles(current_user)
    is_admin = "admin" in user_roles
    is_examiner = "examiner" in user_roles
    is_student = "student" in user_roles and not (is_admin or is_examiner)

    query = db.query(ActivityLog)

    # Authorization filter
    if is_student:
        if user_id is not None and user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Students are not authorized to access other users' activity logs",
            )
        # Always scope student to their own logs
        query = query.filter(ActivityLog.user_id == current_user.id)
    elif is_examiner:
        if user_id is not None:
            query = query.filter(ActivityLog.user_id == user_id)
    elif is_admin:
        if user_id is not None:
            query = query.filter(ActivityLog.user_id == user_id)
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operation restricted to authorized roles",
        )

    # Filter by action / action_type
    if action:
        query = query.filter(ActivityLog.action_type == action)

    # Filter by entity_type
    if entity_type:
        query = query.filter(ActivityLog.entity_type == entity_type)

    # Filter by entity_id
    if entity_id:
        query = query.filter(ActivityLog.entity_id == str(entity_id))

    # Filter by date ranges
    if start_date:
        if start_date.tzinfo:
            start_date = start_date.astimezone(timezone.utc).replace(tzinfo=None)
        query = query.filter(ActivityLog.created_at >= start_date)

    if end_date:
        if end_date.tzinfo:
            end_date = end_date.astimezone(timezone.utc).replace(tzinfo=None)
        query = query.filter(ActivityLog.created_at <= end_date)

    # Total count before pagination
    total = query.count()

    # Pagination calculation
    page = max(1, page)
    page_size = max(1, min(100, page_size))
    offset = (page - 1) * page_size

    items = (
        query.options(joinedload(ActivityLog.user))
        .order_by(desc(ActivityLog.created_at), desc(ActivityLog.id))
        .offset(offset)
        .limit(page_size)
        .all()
    )

    total_pages = (total + page_size - 1) // page_size if total > 0 else 0

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


def get_activity_log_by_id(
    db: Session,
    log_id: int,
    current_user: User,
) -> ActivityLog:
    """
    Retrieve single activity log by ID with role-based access validation.
    """
    log_entry = db.query(ActivityLog).filter(ActivityLog.id == log_id).first()
    if not log_entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Activity log with ID {log_id} not found",
        )

    user_roles = _get_user_roles(current_user)
    if "admin" in user_roles or "examiner" in user_roles:
        return log_entry

    if "student" in user_roles:
        if log_entry.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to view another user's activity log",
            )
        return log_entry

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Operation restricted to authorized roles",
    )


def get_user_activity_logs(
    db: Session,
    target_user_id: int,
    current_user: User,
    page: int = 1,
    page_size: int = 20,
) -> Dict[str, Any]:
    """
    Retrieve activity logs for a specific user.
    Students can only access their own logs.
    """
    user_roles = _get_user_roles(current_user)
    if "student" in user_roles and not ("admin" in user_roles or "examiner" in user_roles):
        if target_user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Students are not authorized to access other users' activity logs",
            )

    return get_activity_logs(
        db=db,
        current_user=current_user,
        user_id=target_user_id,
        page=page,
        page_size=page_size,
    )
