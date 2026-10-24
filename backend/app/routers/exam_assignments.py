from typing import List
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, require_role, get_current_active_user
from app.models.user import User
from app.schemas.exam import (
    ExamAssignmentCreate,
    ExamAssignmentResponse,
    ExamAssignmentListResponse,
    ExamAssignmentBulkResponse,
)
from app.services import exam_service

router = APIRouter(
    prefix="/exams",
    tags=["Exam Assignments"],
    dependencies=[Depends(require_role(["admin", "examiner"]))],
)


@router.post(
    "/{exam_id}/assign",
    response_model=ExamAssignmentBulkResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Assign one or multiple students to an exam",
)
def assign_students(
    exam_id: int,
    assignment_in: ExamAssignmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Assign students to an exam.
    - Examiners can only assign to their own exams.
    - Admins can assign to any exam.
    - Enforces valid student role and rejects duplicates.
    """
    assignments = exam_service.assign_exam_to_students(
        db=db,
        exam_id=exam_id,
        assignment_in=assignment_in,
        current_user=current_user,
    )
    return ExamAssignmentBulkResponse(
        message=f"Successfully assigned {len(assignments)} student(s) to exam {exam_id}",
        assigned_count=len(assignments),
        assignments=[ExamAssignmentResponse.model_validate(a) for a in assignments],
    )


@router.get(
    "/{exam_id}/assignments",
    response_model=ExamAssignmentListResponse,
    status_code=status.HTTP_200_OK,
    summary="List all student assignments for an exam",
)
def get_assignments(
    exam_id: int,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Items per page"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Retrieve paginated assignments for an exam.
    """
    return exam_service.list_exam_assignments(
        db=db,
        exam_id=exam_id,
        current_user=current_user,
        page=page,
        page_size=page_size,
    )


@router.delete(
    "/{exam_id}/assignments/{student_id}",
    status_code=status.HTTP_200_OK,
    summary="Unassign a student from an exam",
)
def unassign_student(
    exam_id: int,
    student_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Remove a student's assignment from an exam.
    """
    exam_service.remove_student_assignment(
        db=db,
        exam_id=exam_id,
        student_id=student_id,
        current_user=current_user,
    )
    return {
        "message": f"Student {student_id} successfully unassigned from exam {exam_id}",
        "exam_id": exam_id,
        "student_id": student_id,
    }
