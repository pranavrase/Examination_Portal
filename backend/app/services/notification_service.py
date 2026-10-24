import math
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Union

from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.notification import Notification, ALLOWED_NOTIFICATION_TYPES, utc_now
from app.models.user import User

logger = logging.getLogger(__name__)


# ==============================================================================
# FUTURE PROVIDER INTERFACE & DISPATCHER
# ==============================================================================

class BaseNotificationProvider(ABC):
    """
    Abstract interface for notification delivery adapters.
    Allows future integrations (Email, SMS, Push, WhatsApp) to attach cleanly
    without modifying core application or database logic.
    """

    @abstractmethod
    def send(self, notification: Notification) -> bool:
        """Send notification via this provider. Return True on success."""
        pass


class InAppNotificationProvider(BaseNotificationProvider):
    """
    Default built-in provider that logs/confirms in-app notification creation.
    Requires no external dependencies or infrastructure.
    """

    def send(self, notification: Notification) -> bool:
        logger.info(
            "InApp notification created: id=%s user_id=%s type=%s",
            notification.id,
            notification.user_id,
            notification.notification_type,
        )
        return True


class NotificationDispatcher:
    """
    Registry and dispatcher for notification providers.
    """

    def __init__(self):
        self._providers: List[BaseNotificationProvider] = [InAppNotificationProvider()]

    def register_provider(self, provider: BaseNotificationProvider) -> None:
        """Register a new external notification provider (e.g. EmailProvider)."""
        self._providers.append(provider)

    def dispatch(self, notification: Notification) -> None:
        """Dispatch notification to all registered delivery channels."""
        for provider in self._providers:
            try:
                provider.send(notification)
            except Exception as e:
                logger.error(
                    "Error delivering notification %s via %s: %s",
                    notification.id,
                    provider.__class__.__name__,
                    str(e),
                )


# Global singleton dispatcher instance
dispatcher = NotificationDispatcher()


# ==============================================================================
# NOTIFICATION SERVICE FUNCTIONS
# ==============================================================================

def create_notification(
    db: Session,
    user_id: int,
    title: str,
    message: str,
    notification_type: str,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    event_key: Optional[str] = None,
) -> Notification:
    """
    Create a notification for a user.
    - Validates recipient existence.
    - Validates notification type.
    - Enforces idempotency via event_key (returns existing without duplicate creation).
    - Dispatches to registered notification providers.
    """
    # 1. Validate recipient
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recipient user {user_id} not found",
        )

    # 2. Validate notification type
    normalized_type = notification_type.upper().strip()
    if normalized_type not in ALLOWED_NOTIFICATION_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid notification type '{notification_type}'. Allowed: {sorted(ALLOWED_NOTIFICATION_TYPES)}",
        )

    # 3. Idempotency check via event_key
    if event_key:
        existing = db.query(Notification).filter(Notification.event_key == event_key).first()
        if existing:
            return existing

    # 4. Create and persist notification
    notification = Notification(
        user_id=user_id,
        title=title[:150],
        message=message,
        notification_type=normalized_type,
        entity_type=entity_type[:50] if entity_type else None,
        entity_id=str(entity_id)[:100] if entity_id is not None else None,
        event_key=event_key[:120] if event_key else None,
        is_read=False,
        read_at=None,
        created_at=utc_now(),
    )

    db.add(notification)
    try:
        db.commit()
        db.refresh(notification)
    except Exception:
        db.rollback()
        # Handle race condition where event_key was committed concurrently
        if event_key:
            existing = db.query(Notification).filter(Notification.event_key == event_key).first()
            if existing:
                return existing
        raise

    # 5. Dispatch to provider hooks
    dispatcher.dispatch(notification)

    return notification


def get_user_notifications(
    db: Session,
    user_id: int,
    page: int = 1,
    page_size: int = 20,
    is_read: Optional[bool] = None,
    notification_type: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Retrieve paginated notifications for the authenticated user only.
    Sorted newest first.
    """
    if page < 1:
        page = 1
    if page_size < 1:
        page_size = 20
    if page_size > 100:
        page_size = 100

    query = db.query(Notification).filter(Notification.user_id == user_id)

    if is_read is not None:
        query = query.filter(Notification.is_read == is_read)

    if notification_type:
        normalized_type = notification_type.upper().strip()
        query = query.filter(Notification.notification_type == normalized_type)

    total = query.count()
    total_pages = math.ceil(total / page_size) if total > 0 else 0

    items = (
        query.order_by(desc(Notification.created_at), desc(Notification.id))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    unread_count = (
        db.query(Notification)
        .filter(Notification.user_id == user_id, Notification.is_read == False)
        .count()
    )

    return {
        "items": items,
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": total_pages,
        "unread_count": unread_count,
    }


def get_unread_count(db: Session, user_id: int) -> int:
    """Return count of unread notifications for a user."""
    return (
        db.query(Notification)
        .filter(Notification.user_id == user_id, Notification.is_read == False)
        .count()
    )


def mark_notification_read(
    db: Session,
    notification_id: int,
    current_user: User,
) -> Notification:
    """
    Mark one notification as read.
    Ensures ownership: only the owner can mark their notification as read.
    Idempotent: marking an already-read notification returns it without error.
    """
    notification = db.query(Notification).filter(Notification.id == notification_id).first()
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )

    if notification.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to modify this notification",
        )

    if not notification.is_read:
        notification.is_read = True
        notification.read_at = utc_now()
        db.commit()
        db.refresh(notification)

        try:
            from app.services.activity_log_service import log_activity
            log_activity(
                db=db,
                user_id=current_user.id,
                action="notification_read",
                description=f"User {current_user.id} marked notification {notification.id} as read",
                entity_type="notification",
                entity_id=str(notification.id),
                commit=True,
            )
        except Exception:
            pass

    return notification


def mark_all_notifications_read(
    db: Session,
    current_user: User,
) -> int:
    """
    Mark all unread notifications for the authenticated user as read.
    Uses efficient bulk UPDATE query without loading records into memory.
    """
    now = utc_now()
    updated_count = (
        db.query(Notification)
        .filter(
            Notification.user_id == current_user.id,
            Notification.is_read == False,
        )
        .update(
            {"is_read": True, "read_at": now},
            synchronize_session=False,
        )
    )
    db.commit()
    return updated_count
