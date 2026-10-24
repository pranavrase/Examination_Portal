from typing import Optional
from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, get_current_active_user, require_role
from app.models.user import User
from app.schemas.exam_attempt import (
    StartAttemptResponse,
    RemainingTimeResponse,
    SubmitAttemptRequest,
    SubmitAttemptResponse,
    AutoSubmitResponse,
)
from app.services import exam_attempt_service

router = APIRouter(
    tags=["Exam Attempts & Submission Engine"],
)


@router.post(
    "/exams/{exam_id}/attempt",
    response_model=StartAttemptResponse,
    status_code=status.HTTP_200_OK,
    summary="Start an exam attempt for an assigned student",
    dependencies=[Depends(require_role(["student"]))],
    responses={
        200: {"description": "Attempt started or existing active attempt resumed"},
        400: {"description": "Exam unpublished, window closed/not opened"},
        401: {"description": "Missing or invalid token"},
        403: {"description": "Forbidden - requires Student role and valid assignment"},
        404: {"description": "Exam not found"},
        409: {"description": "Conflict - attempt already submitted or time expired"},
    },
)
@router.post(
    "/exam-attempts/exams/{exam_id}/attempt",
    response_model=StartAttemptResponse,
    status_code=status.HTTP_200_OK,
    summary="Start an exam attempt (alias path)",
    dependencies=[Depends(require_role(["student"]))],
    include_in_schema=False,
)
def start_student_attempt(
    exam_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Allow an authorized student to start an exam attempt.
    - Validates published status, student assignment, and scheduling window.
    - Sets server-authoritative started_at timestamp.
    - Prevents multiple active attempts (returns existing active attempt).
    - Respects retake rules (rejects already submitted exams).
    """
    result = exam_attempt_service.start_attempt(
        db=db,
        exam_id=exam_id,
        current_user=current_user,
    )
    attempt = result["attempt"]
    return StartAttemptResponse(
        success=True,
        attempt_id=attempt.id,
        exam_id=attempt.exam_id,
        status=attempt.status,
        started_at=attempt.started_at,
        duration_minutes=result["duration_minutes"],
        remaining_seconds=result["remaining_seconds"],
        message=result.get("message", "Exam attempt started successfully"),
    )


@router.get(
    "/exams/{exam_id}/my-attempt",
    status_code=status.HTTP_200_OK,
    summary="Get authenticated student's attempt status for an exam",
    dependencies=[Depends(require_role(["student", "examiner", "admin"]))],
)
@router.get(
    "/exam-attempts/exams/{exam_id}/my-attempt",
    status_code=status.HTTP_200_OK,
    summary="Get authenticated student's attempt status for an exam (alias)",
    dependencies=[Depends(require_role(["student", "examiner", "admin"]))],
    include_in_schema=False,
)
def get_my_attempt_endpoint(
    exam_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Retrieve current student's attempt status for the given exam.
    Returns whether attempt exists and if it is already completed/submitted.
    """
    from app.models.attempt import ExamAttempt
    attempt = db.query(ExamAttempt).filter(
        ExamAttempt.exam_id == exam_id,
        ExamAttempt.student_id == current_user.id,
    ).first()

    if not attempt:
        return {
            "has_attempt": False,
            "attempt_id": None,
            "status": None,
            "is_completed": False,
            "started_at": None,
            "submitted_at": None,
        }

    return {
        "has_attempt": True,
        "attempt_id": attempt.id,
        "status": attempt.status,
        "is_completed": attempt.status in ("submitted", "auto_submitted"),
        "started_at": attempt.started_at,
        "submitted_at": attempt.submitted_at,
    }


@router.get(
    "/exam-attempts/{attempt_id}/remaining-time",
    response_model=RemainingTimeResponse,
    status_code=status.HTTP_200_OK,
    summary="Get authoritative remaining exam time",
    dependencies=[Depends(require_role(["student"]))],
    responses={
        200: {"description": "Remaining time in seconds and attempt status"},
        401: {"description": "Missing or invalid token"},
        403: {"description": "Forbidden - attempt belongs to another student"},
        404: {"description": "Exam attempt not found"},
    },
)
def get_attempt_remaining_time(
    attempt_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Return the server-authoritative remaining time for an exam attempt.
    - Uses server-side started_at and configured exam duration.
    - If remaining time is 0 and attempt is active, triggers auto-submit transition.
    """
    data = exam_attempt_service.get_remaining_time(
        db=db,
        attempt_id=attempt_id,
        current_user=current_user,
    )
    return RemainingTimeResponse(
        attempt_id=data["attempt_id"],
        exam_id=data["exam_id"],
        remaining_seconds=data["remaining_seconds"],
        status=data["status"],
        duration_minutes=data["duration_minutes"],
        started_at=data["started_at"],
    )


@router.post(
    "/exam-attempts/{attempt_id}/submit",
    response_model=SubmitAttemptResponse,
    status_code=status.HTTP_200_OK,
    summary="Submit and finalize an exam attempt",
    dependencies=[Depends(require_role(["student"]))],
    responses={
        200: {"description": "Attempt submitted and scored successfully"},
        401: {"description": "Missing or invalid token"},
        403: {"description": "Forbidden - requires Student role and attempt ownership"},
        404: {"description": "Exam attempt not found"},
        409: {"description": "Attempt is already submitted"},
    },
)
def submit_student_attempt(
    attempt_id: int,
    payload: Optional[SubmitAttemptRequest] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Finalize a student's exam attempt.
    - Locks further modifications, answers, and code drafts.
    - Records official server-determined submitted_at timestamp.
    - Triggers result calculation and scoring engine.
    - Prevents duplicate submissions.
    """
    attempt, result = exam_attempt_service.submit_attempt(
        db=db,
        attempt_id=attempt_id,
        current_user=current_user,
    )

    return SubmitAttemptResponse(
        success=True,
        attempt_id=attempt.id,
        status=attempt.status,
        submitted_at=attempt.submitted_at,
        message="Exam submitted successfully",
        score=float(result.total_marks_obtained) if result else None,
        total_marks=float(result.total_marks_possible) if result else None,
        percentage=float(result.percentage) if result else None,
        pass_fail=result.pass_fail if result else None,
    )


@router.post(
    "/exam-attempts/system/auto-submit",
    response_model=AutoSubmitResponse,
    status_code=status.HTTP_200_OK,
    summary="Trigger auto-submission of expired attempts (System / Maintenance)",
)
def trigger_auto_submit(
    db: Session = Depends(get_db),
):
    """
    Scan for expired in_progress attempts and transition them to 'auto_submitted'.
    Called periodically by the background scheduler.
    """
    count = exam_attempt_service.auto_submit_expired_attempts(db=db)
    return AutoSubmitResponse(
        success=True,
        expired_attempts_submitted=count,
        message=f"Auto-submitted {count} expired attempt(s)",
    )
