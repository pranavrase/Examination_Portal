from typing import Optional
from fastapi import APIRouter, Depends, Query, Path, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, get_current_active_user
from app.models.user import User
from app.schemas.notification import (
    NotificationResponse,
    PaginatedNotificationsResponse,
    UnreadCountResponse,
    MarkAllReadResponse,
)
from app.services import notification_service

router = APIRouter(
    prefix="/notifications",
    tags=["Notifications"],
)


@router.get(
    "",
    response_model=PaginatedNotificationsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get authenticated user's notifications",
)
def get_notifications(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    is_read: Optional[bool] = Query(None, description="Filter by read/unread status"),
    notification_type: Optional[str] = Query(None, description="Filter by notification type"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Retrieve paginated notifications for the currently authenticated user.
    Results are strictly scoped to the requesting user and sorted newest first.
    """
    return notification_service.get_user_notifications(
        db=db,
        user_id=current_user.id,
        page=page,
        page_size=page_size,
        is_read=is_read,
        notification_type=notification_type,
    )


@router.get(
    "/unread-count",
    response_model=UnreadCountResponse,
    status_code=status.HTTP_200_OK,
    summary="Get unread notification count",
)
def get_unread_count(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Return the total number of unread notifications for the currently authenticated user.
    """
    count = notification_service.get_unread_count(
        db=db,
        user_id=current_user.id,
    )
    return {"unread_count": count}


@router.patch(
    "/{notification_id}/read",
    response_model=NotificationResponse,
    status_code=status.HTTP_200_OK,
    summary="Mark a notification as read",
)
def mark_as_read(
    notification_id: int = Path(..., ge=1, description="ID of notification to mark as read"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Mark a specific notification as read.
    Enforces that only the recipient user can mark the notification as read.
    """
    return notification_service.mark_notification_read(
        db=db,
        notification_id=notification_id,
        current_user=current_user,
    )


@router.patch(
    "/read-all",
    response_model=MarkAllReadResponse,
    status_code=status.HTTP_200_OK,
    summary="Mark all unread notifications as read (PATCH)",
)
def mark_all_read_patch(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Mark all unread notifications belonging to the authenticated user as read.
    """
    count = notification_service.mark_all_notifications_read(
        db=db,
        current_user=current_user,
    )
    return {
        "updated_count": count,
        "message": f"Successfully marked {count} notification(s) as read.",
    }


@router.post(
    "/read-all",
    response_model=MarkAllReadResponse,
    status_code=status.HTTP_200_OK,
    summary="Mark all unread notifications as read (POST alternative)",
)
def mark_all_read_post(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Alternative POST endpoint to mark all unread notifications as read.
    """
    count = notification_service.mark_all_notifications_read(
        db=db,
        current_user=current_user,
    )
    return {
        "updated_count": count,
        "message": f"Successfully marked {count} notification(s) as read.",
    }
