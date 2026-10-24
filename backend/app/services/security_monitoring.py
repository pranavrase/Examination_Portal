from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, Union, List
from fastapi import Request, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.security import SecurityEvent
from app.models.user import User


SENSITIVE_KEYS = {
    "password", "passwd", "password_hash", "token", "access_token",
    "refresh_token", "secret", "authorization", "api_key", "credentials"
}

SEVERITY_LEVELS = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}

DEFAULT_SEVERITIES = {
    "failed_login": "LOW",
    "repeated_failed_login": "MEDIUM",
    "expired_token": "LOW",
    "invalid_token": "MEDIUM",
    "attempt_after_expiration": "MEDIUM",
    "permission_denied": "MEDIUM",
    "suspicious_exam_activity": "MEDIUM",
    "suspicious_request": "MEDIUM",
    "rate_limit_violation": "MEDIUM",
    "unauthorized_access": "HIGH",
    "role_violation": "HIGH",
    "cross_user_access_attempt": "HIGH",
    "unauthorized_submission": "HIGH",
    "suspicious_autosave": "HIGH",
    "multiple_active_attempts": "HIGH",
}

EVENT_SEVERITY_MAP = DEFAULT_SEVERITIES


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def sanitize_data(data: Any) -> Any:
    """Recursively redact sensitive credentials (passwords, tokens, API keys) from data."""
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


sanitize_security_data = sanitize_data


def record_security_event(
    db: Session,
    event_type: str,
    severity: Optional[str] = None,
    user_id: Optional[int] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[Union[str, int]] = None,
    description: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    request: Optional[Request] = None,
    log_to_activity: bool = False,
    cooldown_seconds: float = 0.0,
    commit: bool = True,
) -> Optional[SecurityEvent]:
    """
    Record a security-relevant event or violation in the database.
    - Determines severity deterministically if not explicitly provided.
    - Extracts IP address and User-Agent from Request if present.
    - Sanitizes sensitive keys from metadata.
    - Enforces deduplication when cooldown_seconds > 0.
    """
    if request is not None:
        if not ip_address:
            ip_address = request.client.host if request.client else None
        if not user_agent:
            user_agent = request.headers.get("user-agent")

    # Determine severity
    if not severity or severity.upper() not in SEVERITY_LEVELS:
        severity = DEFAULT_SEVERITIES.get(event_type, "LOW")
    else:
        severity = severity.upper()

    clean_metadata = sanitize_data(metadata) if metadata is not None else None
    str_entity_id = str(entity_id) if entity_id is not None else None
    now = utc_now()

    # Deduplication check
    if cooldown_seconds > 0:
        threshold_time = now - timedelta(seconds=cooldown_seconds)
        recent_event = (
            db.query(SecurityEvent)
            .filter(
                SecurityEvent.event_type == event_type,
                SecurityEvent.user_id == user_id,
                SecurityEvent.entity_type == entity_type,
                SecurityEvent.entity_id == str_entity_id,
                SecurityEvent.created_at >= threshold_time,
            )
            .first()
        )
        if recent_event:
            return recent_event

    try:
        event = SecurityEvent(
            user_id=user_id,
            event_type=event_type,
            severity=severity,
            entity_type=entity_type,
            entity_id=str_entity_id,
            description=description,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata_json=clean_metadata,
            created_at=now,
        )
        db.add(event)
        if commit:
            db.commit()
            db.refresh(event)

        # Optional integration bridge with ActivityLog
        if log_to_activity:
            try:
                from app.services.activity_log_service import log_activity
                log_activity(
                    db=db,
                    action="unauthorized_access" if "unauthorized" in event_type else "permission_denied",
                    user_id=user_id,
                    entity_type=entity_type,
                    entity_id=str_entity_id,
                    description=f"Security alert: {description}",
                    metadata=clean_metadata,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    commit=commit,
                )
            except Exception:
                pass

        return event
    except Exception:
        if commit:
            db.rollback()
        return None


def track_failed_login(
    db: Session,
    email: str,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    request: Optional[Request] = None,
    status_code: int = 401,
) -> Optional[SecurityEvent]:
    """
    Monitor failed login attempts.
    Classifies attempt as LOW (failed_login) or MEDIUM/HIGH (repeated_failed_login)
    if threshold of 3 failures within 15 minutes is reached.
    """
    normalized_email = email.lower().strip()
    user = db.query(User).filter(User.email == normalized_email).first()
    user_id = user.id if user else None

    now = utc_now()
    window_start = now - timedelta(minutes=15)

    # Count recent failures for this user or IP
    query = db.query(SecurityEvent).filter(
        SecurityEvent.event_type.in_(["failed_login", "repeated_failed_login"]),
        SecurityEvent.created_at >= window_start,
    )
    if user_id is not None:
        query = query.filter(SecurityEvent.user_id == user_id)
    elif ip_address:
        query = query.filter(SecurityEvent.ip_address == ip_address)

    recent_failures_count = query.count()

    # Threshold rule: 3rd attempt and onwards is repeated_failed_login
    if recent_failures_count >= 2:
        event_type = "repeated_failed_login"
        severity = "MEDIUM"
        description = f"Repeated failed login attempts ({recent_failures_count + 1}) for user {normalized_email}"
    else:
        event_type = "failed_login"
        severity = "LOW"
        description = f"Failed login attempt for user {normalized_email}"

    event = record_security_event(
        db=db,
        event_type=event_type,
        severity=severity,
        user_id=user_id,
        entity_type="user",
        entity_id=str(user_id) if user_id else None,
        description=description,
        metadata={"email": normalized_email, "status_code": status_code, "attempt_count": recent_failures_count + 1},
        ip_address=ip_address,
        user_agent=user_agent,
        request=request,
        commit=True,
    )

    if event_type == "repeated_failed_login" and user_id:
        try:
            from app.services.notification_service import create_notification
            create_notification(
                db=db,
                user_id=user_id,
                title="Security Alert",
                message="Multiple failed login attempts were detected on your account.",
                notification_type="SECURITY_ALERT",
                entity_type="security_event",
                entity_id=str(event.id),
                event_key=f"sec_alert_repeated_login_{user_id}_{event.id}",
            )
        except Exception:
            pass

    return event


def get_security_events(
    db: Session,
    user_id: Optional[int] = None,
    event_type: Optional[str] = None,
    severity: Optional[str] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    page: int = 1,
    page_size: int = 20,
) -> Dict[str, Any]:
    """
    Retrieve paginated security events with filtering for administrators.
    """
    query = db.query(SecurityEvent)

    if user_id is not None:
        query = query.filter(SecurityEvent.user_id == user_id)

    if event_type:
        query = query.filter(SecurityEvent.event_type == event_type)

    if severity:
        query = query.filter(SecurityEvent.severity == severity.upper())

    if entity_type:
        query = query.filter(SecurityEvent.entity_type == entity_type)

    if entity_id:
        query = query.filter(SecurityEvent.entity_id == str(entity_id))

    if start_date:
        if start_date.tzinfo:
            start_date = start_date.astimezone(timezone.utc).replace(tzinfo=None)
        query = query.filter(SecurityEvent.created_at >= start_date)

    if end_date:
        if end_date.tzinfo:
            end_date = end_date.astimezone(timezone.utc).replace(tzinfo=None)
        query = query.filter(SecurityEvent.created_at <= end_date)

    total = query.count()

    page = max(1, page)
    page_size = max(1, min(100, page_size))
    offset = (page - 1) * page_size

    items = (
        query.order_by(desc(SecurityEvent.created_at), desc(SecurityEvent.id))
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


def get_security_event_by_id(db: Session, event_id: int) -> SecurityEvent:
    """Retrieve single security event by ID."""
    event = db.query(SecurityEvent).filter(SecurityEvent.id == event_id).first()
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Security event with ID {event_id} not found",
        )
    return event
