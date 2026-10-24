from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, require_role, get_current_active_user
from app.models.user import User
from app.schemas.exam import (
    ExamCreate,
    ExamUpdate,
    ExamResponse,
    ExamListResponse,
    ExamSettingsUpdate,
    ExamSettingsResponse,
)
from app.services import exam_service

router = APIRouter(
    prefix="/exams",
    tags=["Exam Management"],
    dependencies=[Depends(require_role(["admin", "examiner", "student"]))],
)


@router.post(
    "",
    response_model=ExamResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new exam (Examiner / Admin)",
    dependencies=[Depends(require_role(["admin", "examiner"]))],
)
def create_new_exam(
    exam_in: ExamCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Create a new exam in 'draft' status with its initial configuration settings.
    The authenticated user is recorded as the creator.
    """
    new_exam = exam_service.create_exam(
        db=db,
        exam_in=exam_in,
        creator_id=current_user.id,
    )
    try:
        from app.services.activity_log_service import log_activity
        log_activity(
            db=db,
            action="exam_created",
            user_id=current_user.id,
            entity_type="exam",
            entity_id=str(new_exam.id),
            description=f"Exam '{new_exam.title}' created by User #{current_user.id}",
        )
    except Exception:
        pass
    return new_exam


@router.get(
    "",
    response_model=ExamListResponse,
    status_code=status.HTTP_200_OK,
    summary="List exams with pagination and filters (Examiner sees own, Admin sees all)",
    dependencies=[Depends(require_role(["admin", "examiner"]))],
)
def get_all_exams(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    status: Optional[str] = Query(None, description="Filter by status: draft, published, closed"),
    search: Optional[str] = Query(None, description="Filter by title search keyword"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Retrieve a paginated list of exams.
    Examiners only see their own created exams; Admins can see all exams.
    """
    return exam_service.list_exams(
        db=db,
        current_user=current_user,
        page=page,
        page_size=page_size,
        status_filter=status,
        search=search,
    )


@router.get(
    "/{exam_id}",
    response_model=ExamResponse,
    status_code=status.HTTP_200_OK,
    summary="Get exam details by ID",
)
def get_exam(
    exam_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Retrieve single exam details along with settings.
    Admins can view any exam; Examiners can view their own; Students can view published or assigned exams.
    """
    return exam_service.get_exam_by_id(
        db=db,
        exam_id=exam_id,
        current_user=current_user,
    )


@router.put(
    "/{exam_id}",
    response_model=ExamResponse,
    status_code=status.HTTP_200_OK,
    summary="Update exam details and settings",
    dependencies=[Depends(require_role(["admin", "examiner"]))],
)
def update_existing_exam(
    exam_id: int,
    exam_in: ExamUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Update title, description, or configuration settings of an exam.
    Enforces ownership and lifecycle checks.
    """
    return exam_service.update_exam(
        db=db,
        exam_id=exam_id,
        exam_in=exam_in,
        current_user=current_user,
    )


@router.put(
    "/{exam_id}/settings",
    response_model=ExamSettingsResponse,
    status_code=status.HTTP_200_OK,
    summary="Update exam settings only",
    dependencies=[Depends(require_role(["admin", "examiner"]))],
)
def update_settings(
    exam_id: int,
    settings_in: ExamSettingsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Update only the configuration settings (duration, marks, passing percentage, etc.) of an exam.
    """
    return exam_service.update_exam_settings(
        db=db,
        exam_id=exam_id,
        settings_in=settings_in,
        current_user=current_user,
    )


@router.post(
    "/{exam_id}/publish",
    response_model=ExamResponse,
    status_code=status.HTTP_200_OK,
    summary="Publish an exam",
    dependencies=[Depends(require_role(["admin", "examiner"]))],
)
def publish_existing_exam(
    exam_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Publish a draft exam.
    Transitions status from 'draft' to 'published'.
    """
    pub_exam = exam_service.publish_exam(
        db=db,
        exam_id=exam_id,
        current_user=current_user,
    )
    try:
        from app.services.activity_log_service import log_activity
        log_activity(
            db=db,
            action="exam_published",
            user_id=current_user.id,
            entity_type="exam",
            entity_id=str(pub_exam.id),
            description=f"Exam '{pub_exam.title}' published by User #{current_user.id}",
        )
    except Exception:
        pass
    return pub_exam


@router.delete(
    "/{exam_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete an exam",
    dependencies=[Depends(require_role(["admin", "examiner"]))],
)
def delete_existing_exam(
    exam_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Delete a draft exam.
    Cannot delete published/closed exams or exams with active assignments.
    """
    exam_service.delete_exam(
        db=db,
        exam_id=exam_id,
        current_user=current_user,
    )
    return {
        "message": f"Exam with ID {exam_id} successfully deleted",
        "id": exam_id,
    }
