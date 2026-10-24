from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, Union
from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.models.exam import Exam, ExamSettings, ExamAssignment
from app.models.question import Question, McqOption, CodingQuestion, ExamQuestion
from app.models.attempt import ExamAttempt, AttemptAnswer, CodingSubmission
from app.models.user import User


def utc_now() -> datetime:
    """Return current UTC datetime without tzinfo for database compatibility."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _is_student(user: User) -> bool:
    """Check if the user has the 'student' role."""
    user_roles = {r.name.lower() for r in user.roles}
    if user.role:
        user_roles.add(user.role.lower())
    return "student" in user_roles


def validate_attempt_access(
    db: Session,
    attempt_id: int,
    current_user: User,
) -> ExamAttempt:
    """
    Validate that:
    1. User has the Student role.
    2. Attempt exists.
    3. Attempt belongs to the authenticated student.
    4. Attempt is currently 'in_progress'.
    5. Exam has not expired (duration and schedule window).
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
                event_type="cross_user_access_attempt",
                severity="HIGH",
                user_id=current_user.id,
                entity_type="exam_attempt",
                entity_id=str(attempt_id),
                description=f"User {current_user.id} attempted unauthorized auto-save modification on attempt {attempt_id} belonging to student {attempt.student_id}",
                metadata={"attempt_id": attempt_id, "target_student_id": attempt.student_id, "action": "autosave"},
            )
        except Exception:
            pass
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to modify this attempt",
        )

    if attempt.status != "in_progress":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Exam attempt is no longer active",
        )

    # Server-side authoritative timing & expiration check
    exam = db.query(Exam).options(joinedload(Exam.settings)).filter(Exam.id == attempt.exam_id).first()
    if not exam:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Exam not found",
        )

    if not exam.settings or not exam.settings.duration_minutes:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Exam configuration is incomplete: duration_minutes is not set in exam settings",
        )
    duration_minutes = exam.settings.duration_minutes
    now = utc_now()

    if attempt.started_at:
        expiry_time = attempt.started_at + timedelta(minutes=duration_minutes)
        if now > expiry_time:
            try:
                from app.services.security_monitoring import record_security_event
                record_security_event(
                    db=db,
                    event_type="attempt_after_expiration",
                    severity="MEDIUM",
                    user_id=current_user.id,
                    entity_type="exam_attempt",
                    entity_id=str(attempt_id),
                    description=f"User {current_user.id} attempted auto-save on expired attempt {attempt_id}",
                    metadata={"attempt_id": attempt_id},
                    cooldown_seconds=10.0,
                )
            except Exception:
                pass
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Exam time has expired",
            )

    # Check assignment scheduled_end if configured
    assignment = db.query(ExamAssignment).filter(
        ExamAssignment.exam_id == attempt.exam_id,
        ExamAssignment.student_id == attempt.student_id,
    ).first()
    if assignment and assignment.scheduled_end and now > assignment.scheduled_end:
        try:
            from app.services.security_monitoring import record_security_event
            record_security_event(
                db=db,
                event_type="attempt_after_expiration",
                severity="MEDIUM",
                user_id=current_user.id,
                entity_type="exam_attempt",
                entity_id=str(attempt_id),
                description=f"User {current_user.id} attempted auto-save after assignment scheduled window on attempt {attempt_id}",
                metadata={"attempt_id": attempt_id},
                cooldown_seconds=10.0,
            )
        except Exception:
            pass
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Exam time has expired",
        )

    return attempt


def autosave_mcq_answer(
    db: Session,
    attempt_id: int,
    question_id: int,
    selected_option_id: Optional[int],
    current_user: User,
) -> AttemptAnswer:
    """
    Autosave/update a student's current MCQ answer without submitting or scoring the exam.
    Idempotent: updates existing AttemptAnswer if present, creates new row if absent.
    """
    attempt = validate_attempt_access(db=db, attempt_id=attempt_id, current_user=current_user)

    # Validate question belongs to the attempt's exam
    exam_q = db.query(ExamQuestion).filter(
        ExamQuestion.exam_id == attempt.exam_id,
        ExamQuestion.question_id == question_id,
    ).first()
    if not exam_q:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question does not belong to this exam",
        )

    question = db.query(Question).filter(Question.id == question_id).first()
    if not question or question.question_type != "mcq":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question is not an MCQ question",
        )

    # Validate selected option belongs to the question (if option is selected)
    if selected_option_id is not None:
        option = db.query(McqOption).filter(
            McqOption.id == selected_option_id,
            McqOption.question_id == question_id,
        ).first()
        if not option:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Selected option does not belong to this question",
            )

    now = utc_now()
    try:
        existing_answer = db.query(AttemptAnswer).filter(
            AttemptAnswer.attempt_id == attempt.id,
            AttemptAnswer.question_id == question_id,
        ).first()

        if existing_answer:
            existing_answer.selected_option_id = selected_option_id
            existing_answer.answered_at = now
            existing_answer.updated_at = now
            answer_record = existing_answer
        else:
            answer_record = AttemptAnswer(
                attempt_id=attempt.id,
                question_id=question_id,
                selected_option_id=selected_option_id,
                answered_at=now,
            )
            db.add(answer_record)

        db.commit()
        db.refresh(answer_record)
        return answer_record
    except IntegrityError:
        db.rollback()
        # Concurrency fallback: retry retrieval
        answer_record = db.query(AttemptAnswer).filter(
            AttemptAnswer.attempt_id == attempt.id,
            AttemptAnswer.question_id == question_id,
        ).first()
        if answer_record:
            answer_record.selected_option_id = selected_option_id
            answer_record.answered_at = now
            answer_record.updated_at = now
            db.commit()
            db.refresh(answer_record)
            return answer_record
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Integrity conflict saving answer",
        )
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error autosaving answer: {str(e)}",
        )


def autosave_code_draft(
    db: Session,
    attempt_id: int,
    coding_question_id: int,
    language: str,
    source_code: str,
    current_user: User,
) -> CodingSubmission:
    """
    Autosave/update a student's in-progress source code draft.
    - Operates with is_final = False.
    - Never overwrites or modifies final submissions (is_final = True).
    - Does NOT execute code or invoke Judge0.
    """
    attempt = validate_attempt_access(db=db, attempt_id=attempt_id, current_user=current_user)

    # Resolve coding question (supports both coding_questions.id and questions.id)
    cq = db.query(CodingQuestion).filter(CodingQuestion.id == coding_question_id).first()
    if not cq:
        cq = db.query(CodingQuestion).filter(CodingQuestion.question_id == coding_question_id).first()

    if not cq:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Coding question not found",
        )

    # Validate coding question belongs to the attempt's exam
    exam_q = db.query(ExamQuestion).filter(
        ExamQuestion.exam_id == attempt.exam_id,
        ExamQuestion.question_id == cq.question_id,
    ).first()
    if not exam_q:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question does not belong to this exam",
        )

    # Validate programming language
    allowed_langs = [l.lower() for l in (cq.allowed_languages or [])]
    if allowed_langs and language.lower() not in allowed_langs:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Coding language is not allowed for this question",
        )

    now = utc_now()
    try:
        # Check for existing non-final draft
        existing_draft = db.query(CodingSubmission).filter(
            CodingSubmission.attempt_id == attempt.id,
            CodingSubmission.coding_question_id == cq.id,
            CodingSubmission.is_final == False,
        ).order_by(CodingSubmission.updated_at.desc()).first()

        if existing_draft:
            existing_draft.language = language
            existing_draft.source_code = source_code
            existing_draft.status = "draft"
            existing_draft.updated_at = now
            submission = existing_draft
        else:
            submission = CodingSubmission(
                attempt_id=attempt.id,
                coding_question_id=cq.id,
                language=language,
                source_code=source_code,
                status="draft",
                score=0.0,
                is_final=False,
                submitted_at=now,
            )
            db.add(submission)

        db.commit()
        db.refresh(submission)
        return submission
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error autosaving code draft: {str(e)}",
        )


def autosave_batch_payload(
    db: Session,
    attempt_id: int,
    mcq_answers: Optional[Dict[str, Optional[int]]],
    coding_drafts: Optional[Dict[str, Any]],
    current_user: User,
) -> Dict[str, Any]:
    """
    Process batch autosave payload from frontend useAutoSave hook.
    """
    attempt = validate_attempt_access(db=db, attempt_id=attempt_id, current_user=current_user)

    saved_mcq_count = 0
    saved_coding_count = 0

    if mcq_answers:
        for q_id_str, selected_opt in mcq_answers.items():
            try:
                q_id = int(q_id_str)
            except ValueError:
                continue

            # Autosave single MCQ answer
            autosave_mcq_answer(
                db=db,
                attempt_id=attempt.id,
                question_id=q_id,
                selected_option_id=selected_opt,
                current_user=current_user,
            )
            saved_mcq_count += 1

    if coding_drafts:
        for q_id_str, draft_data in coding_drafts.items():
            try:
                cq_id = int(q_id_str)
            except ValueError:
                continue

            if not isinstance(draft_data, dict):
                continue

            lang = draft_data.get("language")
            code = draft_data.get("source_code") or draft_data.get("code") or ""
            if not lang:
                continue

            autosave_code_draft(
                db=db,
                attempt_id=attempt.id,
                coding_question_id=cq_id,
                language=lang,
                source_code=code,
                current_user=current_user,
            )
            saved_coding_count += 1

    return {
        "success": True,
        "message": "Batch autosave completed successfully",
        "attempt_id": attempt.id,
        "saved_mcq_count": saved_mcq_count,
        "saved_coding_draft_count": saved_coding_count,
    }
