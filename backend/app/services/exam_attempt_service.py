from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, Tuple
from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.models.exam import Exam, ExamSettings, ExamAssignment
from app.models.question import Question, McqOption, CodingQuestion, ExamQuestion
from app.models.attempt import ExamAttempt, AttemptAnswer, CodingSubmission
from app.models.result import Result
from app.models.log import ActivityLog
from app.models.user import User
# Module 2.10: delegate scoring to the dedicated result service
from app.services import result_service as _result_svc


def utc_now() -> datetime:
    """Return current UTC datetime without tzinfo for consistent database timestamps."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _is_student(user: User) -> bool:
    """Check if the user has the 'student' role."""
    user_roles = {r.name.lower() for r in user.roles}
    if user.role:
        user_roles.add(user.role.lower())
    return "student" in user_roles


def log_attempt_activity(
    db: Session,
    user_id: int,
    action_type: str,
    description: str,
    metadata_json: Optional[Dict[str, Any]] = None,
    entity_type: Optional[str] = "exam_attempt",
    entity_id: Optional[Any] = None,
) -> None:
    """Record audit log in activity_logs table via centralized activity logging service."""
    try:
        from app.services.activity_log_service import log_activity
        log_activity(
            db=db,
            action=action_type,
            user_id=user_id,
            entity_type=entity_type,
            entity_id=entity_id,
            description=description,
            metadata=metadata_json,
            commit=True,
        )
    except Exception:
        db.rollback()


def start_attempt(
    db: Session,
    exam_id: int,
    current_user: User,
) -> Dict[str, Any]:
    """
    Allow an authorized student to start an assigned exam.
    Validates:
    - User has student role.
    - Exam exists and is published.
    - Student is assigned to the exam.
    - Exam scheduling window is valid.
    - Student does not already have a finalized attempt.
    - If student already has an active attempt, returns existing attempt.
    """
    if not _is_student(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operation restricted to users with roles: student",
        )

    exam = db.query(Exam).options(joinedload(Exam.settings)).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Exam with ID {exam_id} not found",
        )

    if exam.status != "published":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Exam is not published and cannot be attempted",
        )

    # Validate assignment
    assignment = db.query(ExamAssignment).filter(
        ExamAssignment.exam_id == exam_id,
        ExamAssignment.student_id == current_user.id,
    ).first()

    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not assigned to this exam",
        )

    now = utc_now()

    # Validate schedule window
    if assignment.scheduled_start and now < assignment.scheduled_start:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Exam window has not opened yet",
        )

    if assignment.scheduled_end and now > assignment.scheduled_end:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Exam window has already closed",
        )

    if not exam.settings or not exam.settings.duration_minutes:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Exam configuration is incomplete: duration_minutes is not set in exam settings",
        )
    duration_minutes = exam.settings.duration_minutes

    # Check for existing attempt
    existing_attempt = db.query(ExamAttempt).filter(
        ExamAttempt.exam_id == exam_id,
        ExamAttempt.student_id == current_user.id,
    ).first()

    if existing_attempt:
        if existing_attempt.status in ("submitted", "auto_submitted"):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "message": "Exam attempt has already been submitted and cannot be retaken",
                    "attempt_id": existing_attempt.id,
                    "status": existing_attempt.status,
                },
            )

        # Check if existing in_progress attempt has expired
        elapsed = (now - existing_attempt.started_at).total_seconds() if existing_attempt.started_at else 0
        rem_seconds = max(0, int(duration_minutes * 60 - elapsed))

        if rem_seconds <= 0:
            existing_attempt.status = "auto_submitted"
            existing_attempt.submitted_at = now
            existing_attempt.remaining_seconds_snapshot = 0
            db.commit()
            db.refresh(existing_attempt)
            process_attempt_result(db=db, attempt_id=existing_attempt.id)
            log_attempt_activity(
                db=db,
                user_id=current_user.id,
                action_type="exam_submit",
                description=f"Auto-submitted expired exam attempt {existing_attempt.id}",
                metadata_json={"system_triggered": True, "exam_id": exam_id},
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "message": "Exam time has expired and the attempt was automatically submitted",
                    "attempt_id": existing_attempt.id,
                    "status": existing_attempt.status,
                },
            )

        return {
            "attempt": existing_attempt,
            "duration_minutes": duration_minutes,
            "remaining_seconds": rem_seconds,
            "message": "Existing active exam attempt resumed",
        }

    # Create new attempt
    started_at = now
    remaining_seconds = duration_minutes * 60

    try:
        attempt = ExamAttempt(
            exam_id=exam_id,
            student_id=current_user.id,
            started_at=started_at,
            status="in_progress",
            remaining_seconds_snapshot=remaining_seconds,
        )
        db.add(attempt)
        db.commit()
        db.refresh(attempt)
    except IntegrityError:
        db.rollback()
        # Concurrency race condition: attempt was just created
        attempt = db.query(ExamAttempt).filter(
            ExamAttempt.exam_id == exam_id,
            ExamAttempt.student_id == current_user.id,
        ).first()
        if not attempt:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Conflict initializing exam attempt",
            )
        if attempt.status in ("submitted", "auto_submitted"):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "message": "Exam attempt has already been submitted and cannot be retaken",
                    "attempt_id": attempt.id,
                    "status": attempt.status,
                },
            )

    log_attempt_activity(
        db=db,
        user_id=current_user.id,
        action_type="exam_start",
        description=f"Student {current_user.id} started attempt {attempt.id} for exam {exam_id}",
        metadata_json={"exam_id": exam_id, "attempt_id": attempt.id},
        entity_type="exam_attempt",
        entity_id=attempt.id,
    )

    return {
        "attempt": attempt,
        "duration_minutes": duration_minutes,
        "remaining_seconds": remaining_seconds,
        "message": "Exam attempt started successfully",
    }


def get_remaining_time(
    db: Session,
    attempt_id: int,
    current_user: User,
) -> Dict[str, Any]:
    """
    Return the server-authoritative remaining exam time.
    Calculates time using server-side started_at and configured exam duration.
    If time has expired, auto-submits the attempt.
    """
    attempt = db.query(ExamAttempt).filter(ExamAttempt.id == attempt_id).first()
    if not attempt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Exam attempt not found",
        )

    if attempt.student_id != current_user.id:
        try:
            from app.services.security_monitoring import record_security_event
            record_security_event(
                db=db,
                event_type="cross_user_access_attempt",
                severity="HIGH",
                user_id=current_user.id,
                entity_type="exam_attempt",
                entity_id=str(attempt_id),
                description=f"User {current_user.id} attempted to view attempt {attempt_id} belonging to student {attempt.student_id}",
            )
        except Exception:
            pass
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to view this attempt",
        )

    exam = db.query(Exam).options(joinedload(Exam.settings)).filter(Exam.id == attempt.exam_id).first()
    if not exam or not exam.settings or not exam.settings.duration_minutes:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Exam configuration is incomplete: duration_minutes is not set in exam settings",
        )
    duration_minutes = exam.settings.duration_minutes

    # If already submitted
    if attempt.status in ("submitted", "auto_submitted"):
        return {
            "attempt_id": attempt.id,
            "exam_id": attempt.exam_id,
            "remaining_seconds": 0,
            "status": attempt.status,
            "duration_minutes": duration_minutes,
            "started_at": attempt.started_at,
        }

    now = utc_now()
    elapsed = (now - attempt.started_at).total_seconds() if attempt.started_at else 0
    rem = max(0, int(duration_minutes * 60 - elapsed))

    # Also check assignment scheduled_end
    assignment = db.query(ExamAssignment).filter(
        ExamAssignment.exam_id == attempt.exam_id,
        ExamAssignment.student_id == attempt.student_id,
    ).first()
    if assignment and assignment.scheduled_end:
        window_rem = max(0, int((assignment.scheduled_end - now).total_seconds()))
        rem = min(rem, window_rem)

    if rem <= 0 and attempt.status == "in_progress":
        # Authoritative timer expiration transition
        attempt.status = "auto_submitted"
        attempt.submitted_at = now
        attempt.remaining_seconds_snapshot = 0
        db.commit()
        db.refresh(attempt)
        process_attempt_result(db=db, attempt_id=attempt.id)
        log_attempt_activity(
            db=db,
            user_id=current_user.id,
            action_type="exam_submit",
            description=f"Authoritative timer auto-submitted attempt {attempt.id}",
            metadata_json={"system_triggered": True, "attempt_id": attempt.id},
        )
        try:
            from app.services.notification_service import create_notification
            create_notification(
                db=db,
                user_id=attempt.student_id,
                title="Exam Submitted",
                message="Your examination attempt has been submitted automatically because the exam time expired.",
                notification_type="EXAM_AUTO_SUBMITTED",
                entity_type="exam_attempt",
                entity_id=str(attempt.id),
                event_key=f"auto_submit_attempt_{attempt.id}",
            )
        except Exception:
            pass
        return {
            "attempt_id": attempt.id,
            "exam_id": attempt.exam_id,
            "remaining_seconds": 0,
            "status": "expired",
            "duration_minutes": duration_minutes,
            "started_at": attempt.started_at,
        }

    return {
        "attempt_id": attempt.id,
        "exam_id": attempt.exam_id,
        "remaining_seconds": rem,
        "status": "in_progress",
        "duration_minutes": duration_minutes,
        "started_at": attempt.started_at,
    }


def submit_attempt(
    db: Session,
    attempt_id: int,
    current_user: User,
) -> Tuple[ExamAttempt, Optional[Result]]:
    """
    Manually submit an active exam attempt.
    Locks further modifications, records server timestamp, and triggers scoring.
    """
    if not _is_student(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operation restricted to users with roles: student",
        )

    attempt = db.query(ExamAttempt).filter(ExamAttempt.id == attempt_id).first()
    if not attempt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Exam attempt not found",
        )

    if attempt.student_id != current_user.id:
        try:
            from app.services.security_monitoring import record_security_event
            record_security_event(
                db=db,
                event_type="unauthorized_submission",
                severity="HIGH",
                user_id=current_user.id,
                entity_type="exam_attempt",
                entity_id=str(attempt_id),
                description=f"User {current_user.id} attempted to submit attempt {attempt_id} belonging to student {attempt.student_id}",
            )
        except Exception:
            pass
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to submit this attempt",
        )

    if attempt.status in ("submitted", "auto_submitted"):
        try:
            from app.services.security_monitoring import record_security_event
            record_security_event(
                db=db,
                event_type="attempt_after_expiration",
                severity="MEDIUM",
                user_id=current_user.id,
                entity_type="exam_attempt",
                entity_id=str(attempt_id),
                description=f"User {current_user.id} attempted to submit attempt {attempt_id} which is already {attempt.status}",
            )
        except Exception:
            pass
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Exam attempt has already been submitted",
        )

    now = utc_now()
    exam = db.query(Exam).options(joinedload(Exam.settings)).filter(Exam.id == attempt.exam_id).first()
    if not exam or not exam.settings or not exam.settings.duration_minutes:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Exam configuration is incomplete: duration_minutes is not set in exam settings",
        )
    duration_minutes = exam.settings.duration_minutes

    elapsed = (now - attempt.started_at).total_seconds() if attempt.started_at else 0
    rem = max(0, int(duration_minutes * 60 - elapsed))

    # Atomically finalize attempt
    attempt.status = "submitted"
    attempt.submitted_at = now
    attempt.remaining_seconds_snapshot = rem
    attempt.updated_at = now

    try:
        db.commit()
        db.refresh(attempt)
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error finalizing exam submission: {str(e)}",
        )

    log_attempt_activity(
        db=db,
        user_id=current_user.id,
        action_type="exam_submit",
        description=f"Student {current_user.id} manually submitted attempt {attempt.id}",
        metadata_json={"attempt_id": attempt.id, "submitted_at": now.isoformat()},
        entity_type="exam_attempt",
        entity_id=attempt.id,
    )

    # Trigger scoring calculation
    result = process_attempt_result(db=db, attempt_id=attempt.id)

    return attempt, result


def auto_submit_expired_attempts(db: Session) -> int:
    """
    System task: scan all in_progress exam attempts, detect expired durations,
    and finalize them as 'auto_submitted'.
    Idempotent and safe against race conditions.
    """
    now = utc_now()
    active_attempts = (
        db.query(ExamAttempt)
        .options(joinedload(ExamAttempt.exam).joinedload(Exam.settings))
        .filter(ExamAttempt.status == "in_progress")
        .all()
    )

    auto_submitted_count = 0

    for att in active_attempts:
        if not att.started_at:
            continue

        exam = att.exam
        if not exam or not exam.settings or not exam.settings.duration_minutes:
            continue
        duration_minutes = exam.settings.duration_minutes
        elapsed_seconds = (now - att.started_at).total_seconds()

        # Check duration expiration
        is_expired = elapsed_seconds >= (duration_minutes * 60)

        # Check assignment window expiration if configured
        if not is_expired:
            assignment = db.query(ExamAssignment).filter(
                ExamAssignment.exam_id == att.exam_id,
                ExamAssignment.student_id == att.student_id,
            ).first()
            if assignment and assignment.scheduled_end and now >= assignment.scheduled_end:
                is_expired = True

        if is_expired:
            try:
                att.status = "auto_submitted"
                att.submitted_at = now
                att.remaining_seconds_snapshot = 0
                att.updated_at = now
                db.commit()
                db.refresh(att)

                process_attempt_result(db=db, attempt_id=att.id)

                log_attempt_activity(
                    db=db,
                    user_id=att.student_id,
                    action_type="exam_submit",
                    description=f"System background auto-submitted expired attempt {att.id}",
                    metadata_json={"system_triggered": True, "attempt_id": att.id},
                )
                try:
                    from app.services.notification_service import create_notification
                    create_notification(
                        db=db,
                        user_id=att.student_id,
                        title="Exam Submitted",
                        message="Your examination attempt has been submitted automatically because the exam time expired.",
                        notification_type="EXAM_AUTO_SUBMITTED",
                        entity_type="exam_attempt",
                        entity_id=str(att.id),
                        event_key=f"auto_submit_attempt_{att.id}",
                    )
                except Exception:
                    pass
                auto_submitted_count += 1
            except Exception:
                db.rollback()

    return auto_submitted_count


def process_attempt_result(db: Session, attempt_id: int) -> Optional[Result]:
    """
    Calculate and persist the final exam result for an attempt.

    This is the Module 2.9 → Module 2.10 integration bridge.
    All calculation logic lives in result_service.calculate_final_score().
    Returns None silently on failure (to prevent submission from rolling back).
    """
    try:
        return _result_svc.calculate_final_score(db=db, attempt_id=attempt_id)
    except Exception:
        # Never let scoring failure block submission persistence
        return None
