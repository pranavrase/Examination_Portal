"""
Module 2.10 — Result Calculation Engine
========================================
Service functions:
  - calculate_final_score(db, attempt_id)  → Result
  - apply_negative_marking(effective_marks, neg_ratio) → float
  - determine_pass_fail(percentage, passing_pct) → bool

Design principles:
  * All scoring values come exclusively from the database.
  * Idempotent: calling twice updates existing Result, never duplicates it.
  * Transactional: full rollback on any failure.
  * No Judge0 calls — coding score is read from CodingSubmission.score
    (already written by Module 2.7 after Judge0 evaluation).
  * Negative marking is applied once per incorrect MCQ only.
  * Unanswered MCQ questions earn zero marks (no penalty).
  * Score floor: total_marks_obtained is allowed to go negative only if
    the exam configuration produces that result; we do NOT clamp to zero
    at the service level (clamping is configurable via the caller).
"""

from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Optional, Tuple, List, Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.models.exam import Exam, ExamSettings
from app.models.question import Question, McqOption, CodingQuestion, ExamQuestion
from app.models.attempt import ExamAttempt, AttemptAnswer, CodingSubmission, ExecutionResult
from app.models.result import Result
from app.models.user import User


def utc_now() -> datetime:
    """Return current UTC datetime without tzinfo, consistent with other services."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _decimal(value: Any) -> Decimal:
    """Convert a value to Decimal for precise arithmetic."""
    if value is None:
        return Decimal("0")
    return Decimal(str(value))


def _round2(value: Decimal) -> Decimal:
    """Round a Decimal to 2 decimal places using ROUND_HALF_UP."""
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _user_roles(user: User) -> set:
    """Return lowercase role names for the user."""
    roles = {r.name.lower() for r in user.roles}
    if user.role:
        roles.add(user.role.lower())
    return roles


def _is_admin(user: User) -> bool:
    return "admin" in _user_roles(user)


def _is_examiner(user: User) -> bool:
    return "examiner" in _user_roles(user)


def _is_student(user: User) -> bool:
    return "student" in _user_roles(user)


# ---------------------------------------------------------------------------
# Public API — core scoring functions
# ---------------------------------------------------------------------------

def apply_negative_marking(effective_marks: float, neg_ratio: float) -> float:
    """
    Calculate the penalty for an incorrect MCQ answer.

    Args:
        effective_marks: marks the question is worth (positive float)
        neg_ratio:       negative_marking_ratio from ExamSettings (e.g. 0.25)

    Returns:
        Negative float representing the penalty (e.g. -0.5 for 2-mark question
        with 0.25 ratio).  Always <= 0.

    Example:
        effective_marks=2, neg_ratio=0.25  →  -(2 * 0.25) = -0.5
    """
    if neg_ratio <= 0:
        return 0.0
    penalty = _decimal(effective_marks) * _decimal(neg_ratio)
    return -float(_round2(penalty))


def determine_pass_fail(percentage: float, passing_pct: float) -> bool:
    """
    Determine if a student passes.

    Args:
        percentage:  calculated percentage (0–100+)
        passing_pct: passing_percentage from ExamSettings

    Returns:
        True if percentage >= passing_pct (boundary inclusive), else False.
    """
    return Decimal(str(percentage)) >= Decimal(str(passing_pct))


def calculate_final_score(
    db: Session,
    attempt_id: int,
) -> Result:
    """
    Calculate and persist the final exam result for a submitted attempt.

    Responsibilities:
      1. Validate attempt exists and is finalized.
      2. Load exam settings.
      3. Load exam questions (MCQ + coding).
      4. Score MCQs from persisted AttemptAnswer + server-side MCQOption.is_correct.
      5. Apply negative marking per question (never applied twice).
      6. Score coding questions from best CodingSubmission.score per question.
      7. Compute total_marks_obtained, total_marks_possible, percentage, pass_fail.
      8. Upsert Result row (idempotent).
      9. Update AttemptAnswer.is_correct / marks_awarded for auditability.

    Raises:
        HTTPException 404  if attempt not found.
        HTTPException 409  if attempt is still in_progress.
        HTTPException 500  on unexpected DB failure.

    Returns:
        The persisted Result ORM object.
    """
    # ── 1. Load attempt ──────────────────────────────────────────────────────
    attempt = (
        db.query(ExamAttempt)
        .options(joinedload(ExamAttempt.exam).joinedload(Exam.settings))
        .filter(ExamAttempt.id == attempt_id)
        .first()
    )
    if not attempt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Exam attempt {attempt_id} not found",
        )

    # ── 2. Validate state ────────────────────────────────────────────────────
    if attempt.status not in ("submitted", "auto_submitted"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot calculate result for an attempt with status '{attempt.status}'. The attempt must be submitted or auto-submitted first.",
        )

    exam = attempt.exam
    settings: Optional[ExamSettings] = exam.settings if exam else None

    passing_pct = float(settings.passing_percentage) if (settings and settings.passing_percentage is not None) else 40.0
    neg_ratio = float(settings.negative_marking_ratio) if (settings and settings.negative_marking_ratio is not None) else 0.0

    # ── 3. Load exam questions ───────────────────────────────────────────────
    exam_questions: List[ExamQuestion] = (
        db.query(ExamQuestion)
        .filter(ExamQuestion.exam_id == attempt.exam_id)
        .all()
    )

    if not exam_questions:
        # Exam has no questions; trivial zero-mark result
        res_record = _upsert_result(db, attempt.id, Decimal("0"), Decimal("0"), Decimal("0"), False)
        try:
            from app.services.notification_service import create_notification
            create_notification(
                db=db,
                user_id=attempt.student_id,
                title="Result Available",
                message="Your result for the examination is now available.",
                notification_type="RESULT_AVAILABLE",
                entity_type="result",
                entity_id=str(res_record.id),
                event_key=f"result_attempt_{attempt.id}",
            )
        except Exception:
            pass
        return res_record

    q_ids = [eq.question_id for eq in exam_questions]

    # Load Question rows with options eagerly
    questions: List[Question] = (
        db.query(Question)
        .options(
            joinedload(Question.mcq_options),
            joinedload(Question.coding_details),
        )
        .filter(Question.id.in_(q_ids))
        .all()
    )
    q_map: Dict[int, Question] = {q.id: q for q in questions}

    # Effective marks per exam-question (override takes priority)
    def _effective_marks(eq: ExamQuestion) -> Decimal:
        if eq.marks_override is not None:
            return _decimal(eq.marks_override)
        q = q_map.get(eq.question_id)
        if q:
            return _decimal(q.marks)
        return Decimal("1")  # fallback; should not happen

    # ── 4. Load answers ──────────────────────────────────────────────────────
    answers: List[AttemptAnswer] = (
        db.query(AttemptAnswer)
        .filter(AttemptAnswer.attempt_id == attempt.id)
        .all()
    )
    ans_map: Dict[int, AttemptAnswer] = {a.question_id: a for a in answers}

    # ── 5. Separate MCQ and coding exam-questions ────────────────────────────
    mcq_eqs = [eq for eq in exam_questions if q_map.get(eq.question_id) and q_map[eq.question_id].question_type == "mcq"]
    coding_eqs = [eq for eq in exam_questions if q_map.get(eq.question_id) and q_map[eq.question_id].question_type == "coding"]

    # ── 6. MCQ Scoring ───────────────────────────────────────────────────────
    mcq_possible = Decimal("0")
    mcq_obtained = Decimal("0")
    negative_applied = Decimal("0")

    for eq in mcq_eqs:
        em = _effective_marks(eq)
        mcq_possible += em

        ans = ans_map.get(eq.question_id)
        q = q_map[eq.question_id]

        if ans is None or ans.selected_option_id is None:
            # Unanswered — zero marks, no penalty
            if ans:
                ans.is_correct = None
                ans.marks_awarded = Decimal("0")
            continue

        # Determine correctness from server-side MCQOption.is_correct
        selected_opt = next(
            (o for o in q.mcq_options if o.id == ans.selected_option_id),
            None,
        )

        if selected_opt is None:
            # Option not found (data inconsistency) — treat as unanswered
            ans.is_correct = None
            ans.marks_awarded = Decimal("0")
            continue

        if selected_opt.is_correct:
            awarded = em
            ans.is_correct = True
            ans.marks_awarded = awarded
            mcq_obtained += awarded
        else:
            # apply_negative_marking returns a negative float; convert back
            penalty = _round2(_decimal(apply_negative_marking(float(em), neg_ratio)))
            ans.is_correct = False
            ans.marks_awarded = penalty          # stored as negative or 0
            mcq_obtained += penalty
            negative_applied += abs(penalty)

    # ── 7. Coding Scoring ────────────────────────────────────────────────────
    coding_possible = Decimal("0")
    coding_obtained = Decimal("0")

    for eq in coding_eqs:
        em = _effective_marks(eq)
        coding_possible += em

        q = q_map[eq.question_id]
        cq: Optional[CodingQuestion] = q.coding_details

        if cq is None:
            # No CodingQuestion row — 0 marks for this question
            continue

        # Load all submissions for this coding question in this attempt
        submissions: List[CodingSubmission] = (
            db.query(CodingSubmission)
            .options(joinedload(CodingSubmission.execution_results))
            .filter(
                CodingSubmission.attempt_id == attempt.id,
                CodingSubmission.coding_question_id == cq.id,
            )
            .all()
        )

        best_score = Decimal("0")
        for sub in submissions:
            sub_score = Decimal("0")
            # If execution_results are present, calculate pro-rated test case score
            if sub.execution_results:
                total_cases = len(sub.execution_results)
                passed_cases = sum(1 for r in sub.execution_results if r.verdict == "passed")
                if total_cases > 0:
                    sub_score = _round2((_decimal(passed_cases) / _decimal(total_cases)) * em)
            if sub.score is not None:
                stored_score = _decimal(sub.score)
                if stored_score > sub_score:
                    sub_score = stored_score

            if sub_score > best_score:
                best_score = sub_score

        awarded = _round2(min(best_score, em))  # cap at question marks
        coding_obtained += awarded

    # ── 8. Totals ────────────────────────────────────────────────────────────
    total_possible = _round2(mcq_possible + coding_possible)
    total_obtained = _round2(mcq_obtained + coding_obtained)

    # Percentage — safe against division by zero
    if total_possible > 0:
        percentage = _round2((total_obtained / total_possible) * Decimal("100"))
    else:
        percentage = Decimal("0")

    pass_fail_result = determine_pass_fail(float(percentage), passing_pct)

    # ── 9. Persist answers with corrected is_correct/marks_awarded ───────────
    try:
        db.flush()  # write AttemptAnswer updates without committing yet
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to persist answer scoring data",
        )

    # ── 10. Upsert Result ────────────────────────────────────────────────────
    res_record = _upsert_result(db, attempt.id, total_obtained, total_possible, percentage, pass_fail_result)

    # ── 11. Trigger Ranking Engine (Module 2.11) ─────────────────────────────
    try:
        from app.services import ranking_service
        ranking_service.compute_rankings_for_exam(exam_id=attempt.exam_id, db=db)
    except Exception:
        # Non-blocking: ranking computation failure must not fail result return
        pass

    # ── 12. Activity Log (Module 2.13) ───────────────────────────────────────
    try:
        from app.services.activity_log_service import log_activity
        log_activity(
            db=db,
            action="result_calculated",
            user_id=attempt.student_id,
            entity_type="exam_attempt",
            entity_id=str(attempt.id),
            description=f"Result calculated for attempt {attempt.id}: {total_obtained}/{total_possible} ({percentage}%)",
            metadata={
                "exam_id": attempt.exam_id,
                "attempt_id": attempt.id,
                "total_marks_obtained": float(total_obtained),
                "total_marks_possible": float(total_possible),
                "percentage": float(percentage),
                "pass_fail": pass_fail_result,
            },
            commit=True,
        )
    except Exception:
        pass

    # ── 13. Notification Service (Module 2.15) ──────────────────────────────
    try:
        from app.services.notification_service import create_notification
        create_notification(
            db=db,
            user_id=attempt.student_id,
            title="Result Available",
            message="Your result for the examination is now available.",
            notification_type="RESULT_AVAILABLE",
            entity_type="result",
            entity_id=str(res_record.id),
            event_key=f"result_attempt_{attempt.id}",
        )
    except Exception:
        pass

    return res_record


def _upsert_result(
    db: Session,
    attempt_id: int,
    total_obtained: Decimal,
    total_possible: Decimal,
    percentage: Decimal,
    pass_fail: bool,
) -> Result:
    """
    Create or update a Result row for the given attempt_id.
    Idempotent — never creates a duplicate row.
    Uses a single transaction with full rollback on failure.
    """
    now = utc_now()
    try:
        existing = db.query(Result).filter(Result.attempt_id == attempt_id).first()
        if existing:
            existing.total_marks_obtained = total_obtained
            existing.total_marks_possible = total_possible
            existing.percentage = percentage
            existing.pass_fail = pass_fail
            existing.calculated_at = now
            existing.updated_at = now
            result_record = existing
        else:
            result_record = Result(
                attempt_id=attempt_id,
                total_marks_obtained=total_obtained,
                total_marks_possible=total_possible,
                percentage=percentage,
                pass_fail=pass_fail,
                calculated_at=now,
            )
            db.add(result_record)

        db.commit()
        db.refresh(result_record)

        # Log result_calculated activity (Module 2.13)
        try:
            from app.services.activity_log_service import log_activity
            att = db.query(ExamAttempt).filter(ExamAttempt.id == attempt_id).first()
            s_id = att.student_id if att else None
            ex_id = att.exam_id if att else None
            log_activity(
                db=db,
                action="result_calculated",
                user_id=s_id,
                entity_type="exam_attempt",
                entity_id=str(attempt_id),
                description=f"Result calculated for attempt {attempt_id}: {total_obtained}/{total_possible} ({percentage}%)",
                metadata={
                    "exam_id": ex_id,
                    "attempt_id": attempt_id,
                    "total_marks_obtained": float(total_obtained),
                    "total_marks_possible": float(total_possible),
                    "percentage": float(percentage),
                    "pass_fail": pass_fail,
                },
                commit=True,
            )
        except Exception:
            pass

        return result_record

    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to persist exam result: {str(exc)}",
        )


# ---------------------------------------------------------------------------
# Authorization helpers for the router
# ---------------------------------------------------------------------------

def get_result_for_student(
    db: Session,
    attempt_id: int,
    current_user: User,
) -> Tuple[Result, ExamAttempt]:
    """
    Fetch a Result, enforcing ownership rules:
      - Student → own attempt only
      - Examiner → any attempt (they own the exam)
      - Admin → any attempt

    Returns (Result, ExamAttempt) or raises HTTPException.
    """
    attempt = db.query(ExamAttempt).filter(ExamAttempt.id == attempt_id).first()
    if not attempt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Exam attempt {attempt_id} not found",
        )

    # Authorization check
    if _is_admin(current_user):
        pass  # full access
    elif _is_examiner(current_user):
        # Examiners can see results for exams they created
        exam = db.query(Exam).filter(Exam.id == attempt.exam_id).first()
        if exam and exam.created_by != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Examiners can only view results for their own exams",
            )
    else:
        # Student — own attempt only
        if attempt.student_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to view another student's result",
            )

    result = db.query(Result).filter(Result.attempt_id == attempt_id).first()
    if not result:
        # If attempt is finalized, try to calculate on-demand
        if attempt.status in ("submitted", "auto_submitted"):
            result = calculate_final_score(db=db, attempt_id=attempt_id)
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Result not yet available. The attempt may still be in progress.",
            )

    return result, attempt


def get_results_for_exam(
    db: Session,
    exam_id: int,
    current_user: User,
) -> List[Tuple[Result, ExamAttempt]]:
    """
    Fetch all results for an exam.
    Admin → all exams.
    Examiner → exams they created only.
    Student → not permitted.
    """
    if _is_student(current_user) and not _is_admin(current_user) and not _is_examiner(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Students cannot list all exam results",
        )

    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Exam {exam_id} not found",
        )

    if _is_examiner(current_user) and not _is_admin(current_user):
        if exam.created_by != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only view results for exams you created",
            )

    attempts: List[ExamAttempt] = (
        db.query(ExamAttempt)
        .filter(
            ExamAttempt.exam_id == exam_id,
            ExamAttempt.status.in_(["submitted", "auto_submitted"]),
        )
        .all()
    )

    pairs = []
    for att in attempts:
        result = db.query(Result).filter(Result.attempt_id == att.id).first()
        if result:
            pairs.append((result, att))

    return pairs
