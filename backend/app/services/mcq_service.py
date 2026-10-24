import random
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.models.exam import Exam, ExamSettings, ExamAssignment
from app.models.question import Question, McqOption, ExamQuestion
from app.models.attempt import ExamAttempt, AttemptAnswer
from app.models.user import User


def utc_now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _is_admin(user: User) -> bool:
    """Check if user has admin privileges."""
    user_roles = {r.name.lower() for r in user.roles}
    if user.role:
        user_roles.add(user.role.lower())
    return "admin" in user_roles


def _is_examiner(user: User) -> bool:
    """Check if user has examiner privileges."""
    user_roles = {r.name.lower() for r in user.roles}
    if user.role:
        user_roles.add(user.role.lower())
    return "examiner" in user_roles


def validate_attempt_owner(attempt: ExamAttempt, current_user: User) -> None:
    """
    Ensure the current user is the owner of the attempt or an admin/examiner.
    Raises HTTP 403 Forbidden if not authorized.
    """
    if _is_admin(current_user) or _is_examiner(current_user):
        return
    if attempt.student_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: you do not have permission to access another student's exam attempt",
        )


def get_or_create_attempt(db: Session, exam_id: int, current_user: User) -> ExamAttempt:
    """
    Get existing active attempt or create a new one for an assigned student.
    """
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Exam with ID {exam_id} not found",
        )

    if exam.status != "published" and not (_is_admin(current_user) or (exam.created_by == current_user.id)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Exam is not published and cannot be attempted",
        )

    # Check assignment for students
    if not (_is_admin(current_user) or (exam.created_by == current_user.id)):
        assignment = db.query(ExamAssignment).filter(
            ExamAssignment.exam_id == exam_id,
            ExamAssignment.student_id == current_user.id,
        ).first()
        if not assignment:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not assigned to this exam",
            )

    # Look for existing attempt
    attempt = db.query(ExamAttempt).filter(
        ExamAttempt.exam_id == exam_id,
        ExamAttempt.student_id == current_user.id,
    ).first()

    if attempt:
        is_privileged = _is_admin(current_user) or (exam.created_by == current_user.id)
        if attempt.status in ("submitted", "auto_submitted") and not is_privileged:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "message": "Exam attempt has already been submitted and cannot be retaken",
                    "attempt_id": attempt.id,
                    "status": attempt.status,
                },
            )
        # Check if attempt time has expired
        if attempt.started_at and exam.settings and exam.settings.duration_minutes and not is_privileged:
            elapsed = (utc_now() - attempt.started_at).total_seconds()
            if elapsed >= exam.settings.duration_minutes * 60:
                attempt.status = "auto_submitted"
                attempt.submitted_at = utc_now()
                attempt.remaining_seconds_snapshot = 0
                try:
                    db.commit()
                    db.refresh(attempt)
                    from app.services.exam_attempt_service import process_attempt_result
                    process_attempt_result(db=db, attempt_id=attempt.id)
                except Exception:
                    db.rollback()
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "message": "Exam time has expired and the attempt was automatically submitted",
                        "attempt_id": attempt.id,
                        "status": attempt.status,
                    },
                )
        return attempt

    try:
        attempt = ExamAttempt(
            exam_id=exam_id,
            student_id=current_user.id,
            started_at=utc_now(),
            status="in_progress",
        )
        db.add(attempt)
        db.commit()
        db.refresh(attempt)
    except IntegrityError:
        db.rollback()
        attempt = db.query(ExamAttempt).filter(
            ExamAttempt.exam_id == exam_id,
            ExamAttempt.student_id == current_user.id,
        ).first()
        if not attempt:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Conflict initializing exam attempt",
            )
        is_privileged = _is_admin(current_user) or (exam.created_by == current_user.id)
        if attempt.status in ("submitted", "auto_submitted") and not is_privileged:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "message": "Exam attempt has already been submitted and cannot be retaken",
                    "attempt_id": attempt.id,
                    "status": attempt.status,
                },
            )
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error initializing exam attempt: {str(e)}",
        )

    return attempt


def generate_randomized_question_set(
    db: Session,
    exam_id: int,
    current_user: User,
) -> Dict[str, Any]:
    """
    Generate randomized MCQ question set for a student attempt.
    - Excludes coding questions.
    - Applies question randomization per attempt seed if enabled.
    - Applies option randomization per attempt+question seed if enabled.
    - Anti-leak: NEVER exposes is_correct.
    - Attaches previously recorded selected_option_id if any.
    """
    attempt = get_or_create_attempt(db=db, exam_id=exam_id, current_user=current_user)
    exam = db.query(Exam).options(joinedload(Exam.settings)).filter(Exam.id == exam_id).first()

    # Query all MCQ exam_questions mapped to this exam
    exam_questions = db.query(ExamQuestion).join(
        Question, ExamQuestion.question_id == Question.id
    ).filter(
        ExamQuestion.exam_id == exam_id,
        Question.question_type == "mcq",
    ).order_by(ExamQuestion.question_order.asc()).all()

    # Fetch question entities and recorded answers
    q_ids = [eq.question_id for eq in exam_questions]
    questions = db.query(Question).options(joinedload(Question.mcq_options)).filter(Question.id.in_(q_ids)).all() if q_ids else []
    q_map = {q.id: q for q in questions}

    # Fetch recorded answers for this attempt
    recorded_answers = db.query(AttemptAnswer).filter(AttemptAnswer.attempt_id == attempt.id).all()
    answer_map = {a.question_id: a.selected_option_id for a in recorded_answers}

    # Pair exam_question with question entity
    paired_list = []
    for eq in exam_questions:
        q = q_map.get(eq.question_id)
        if q and q.question_type == "mcq":
            paired_list.append((eq, q))

    # Apply Question Randomization if configured
    randomize_q = exam.settings.randomize_questions if (exam and exam.settings) else False
    if randomize_q:
        rng_q = random.Random(attempt.id * 10007 + exam_id)
        rng_q.shuffle(paired_list)

    randomize_opt = exam.settings.randomize_options if (exam and exam.settings) else False
    output_questions = []

    for eq, q in paired_list:
        effective_marks = float(eq.marks_override) if eq.marks_override is not None else float(q.marks)
        options = list(q.mcq_options)

        if randomize_opt:
            rng_opt = random.Random(attempt.id * 10007 + q.id * 101)
            rng_opt.shuffle(options)

        safe_options = [
            {"id": opt.id, "option_text": opt.option_text}
            for opt in options
        ]

        output_questions.append({
            "question_id": q.id,
            "question_text": q.question_text,
            "marks": effective_marks,
            "options": safe_options,
            "selected_option_id": answer_map.get(q.id),
        })

    if not exam or not exam.settings or not exam.settings.duration_minutes:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Exam configuration is incomplete: duration_minutes is not set in exam settings",
        )
    duration = exam.settings.duration_minutes

    return {
        "exam_id": exam_id,
        "attempt_id": attempt.id,
        "status": attempt.status,
        "duration_minutes": duration,
        "total_mcq_questions": len(output_questions),
        "questions": output_questions,
    }


def record_mcq_answer(
    db: Session,
    attempt_id: int,
    question_id: int,
    selected_option_id: int,
    current_user: User,
) -> AttemptAnswer:
    """
    Record or update an MCQ answer for an active attempt.
    - Validates student ownership and 'in_progress' status.
    - Validates question belongs to the exam and option belongs to question.
    - Server-side calculates correctness & marks (including negative marking).
    - Guarantees exactly one answer row per (attempt_id, question_id).
    """
    attempt = db.query(ExamAttempt).filter(ExamAttempt.id == attempt_id).first()
    if not attempt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Exam attempt with ID {attempt_id} not found",
        )

    validate_attempt_owner(attempt, current_user)

    if attempt.status != "in_progress":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot record or modify answers: exam attempt is already in '{attempt.status}' state",
        )

    # Validate question belongs to the exam
    exam_q = db.query(ExamQuestion).filter(
        ExamQuestion.exam_id == attempt.exam_id,
        ExamQuestion.question_id == question_id,
    ).first()

    if not exam_q:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Question with ID {question_id} is not mapped to this exam",
        )

    question = db.query(Question).filter(Question.id == question_id).first()
    if not question or question.question_type != "mcq":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Question with ID {question_id} is not an MCQ question",
        )

    # Validate option belongs to question
    option = db.query(McqOption).filter(
        McqOption.id == selected_option_id,
        McqOption.question_id == question_id,
    ).first()

    if not option:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Selected option with ID {selected_option_id} does not belong to question {question_id}",
        )

    # Calculate marks and correctness server-side
    exam = db.query(Exam).options(joinedload(Exam.settings)).filter(Exam.id == attempt.exam_id).first()
    effective_marks = float(exam_q.marks_override) if exam_q.marks_override is not None else float(question.marks)
    neg_ratio = float(exam.settings.negative_marking_ratio) if (exam and exam.settings and exam.settings.negative_marking_ratio) else 0.0

    is_correct = bool(option.is_correct)
    if is_correct:
        marks_awarded = effective_marks
    else:
        marks_awarded = -1.0 * (effective_marks * neg_ratio)

    try:
        # Upsert AttemptAnswer
        existing_answer = db.query(AttemptAnswer).filter(
            AttemptAnswer.attempt_id == attempt_id,
            AttemptAnswer.question_id == question_id,
        ).first()

        now = utc_now()
        if existing_answer:
            existing_answer.selected_option_id = selected_option_id
            existing_answer.is_correct = is_correct
            existing_answer.marks_awarded = marks_awarded
            existing_answer.answered_at = now
            answer_record = existing_answer
        else:
            answer_record = AttemptAnswer(
                attempt_id=attempt_id,
                question_id=question_id,
                selected_option_id=selected_option_id,
                is_correct=is_correct,
                marks_awarded=marks_awarded,
                answered_at=now,
            )
            db.add(answer_record)

        db.commit()
        db.refresh(answer_record)
        return answer_record
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Integrity conflict recording answer: {str(e.orig)}",
        )
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error recording answer: {str(e)}",
        )


def get_attempt_answers(
    db: Session,
    attempt_id: int,
    current_user: User,
) -> Dict[str, Any]:
    """
    Retrieve all recorded answers for an attempt without leaking correctness during active exam.
    """
    attempt = db.query(ExamAttempt).filter(ExamAttempt.id == attempt_id).first()
    if not attempt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Exam attempt with ID {attempt_id} not found",
        )

    validate_attempt_owner(attempt, current_user)

    answers = db.query(AttemptAnswer).filter(AttemptAnswer.attempt_id == attempt_id).all()
    items = [
        {
            "question_id": a.question_id,
            "selected_option_id": a.selected_option_id,
            "answered_at": a.answered_at,
        }
        for a in answers
    ]

    return {
        "attempt_id": attempt.id,
        "status": attempt.status,
        "answers": items,
    }


def score_attempt_mcqs(
    db: Session,
    attempt_id: int,
    current_user: User,
) -> Dict[str, Any]:
    """
    Score the MCQ portion of an attempt.
    """
    attempt = db.query(ExamAttempt).filter(ExamAttempt.id == attempt_id).first()
    if not attempt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Exam attempt with ID {attempt_id} not found",
        )

    validate_attempt_owner(attempt, current_user)

    exam_questions = db.query(ExamQuestion).join(
        Question, ExamQuestion.question_id == Question.id
    ).filter(
        ExamQuestion.exam_id == attempt.exam_id,
        Question.question_type == "mcq",
    ).all()

    q_ids = [eq.question_id for eq in exam_questions]
    questions = db.query(Question).filter(Question.id.in_(q_ids)).all()
    q_map = {q.id: q for q in questions}

    recorded_answers = db.query(AttemptAnswer).filter(AttemptAnswer.attempt_id == attempt_id).all()
    answer_map = {a.question_id: a for a in recorded_answers}

    total_possible = 0.0
    total_obtained = 0.0
    correct_count = 0
    incorrect_count = 0
    answered_count = 0
    breakdown = []

    for eq in exam_questions:
        q = q_map.get(eq.question_id)
        effective_marks = float(eq.marks_override) if eq.marks_override is not None else (float(q.marks) if q else 1.0)
        total_possible += effective_marks

        ans = answer_map.get(eq.question_id)
        if ans and ans.selected_option_id is not None:
            answered_count += 1
            is_corr = bool(ans.is_correct)
            awarded = float(ans.marks_awarded) if ans.marks_awarded is not None else 0.0
            if is_corr:
                correct_count += 1
            else:
                incorrect_count += 1
            total_obtained += awarded

            breakdown.append({
                "question_id": eq.question_id,
                "marks_possible": effective_marks,
                "selected_option_id": ans.selected_option_id,
                "is_correct": is_corr,
                "marks_awarded": awarded,
            })
        else:
            breakdown.append({
                "question_id": eq.question_id,
                "marks_possible": effective_marks,
                "selected_option_id": None,
                "is_correct": None,
                "marks_awarded": 0.0,
            })

    unanswered_count = len(exam_questions) - answered_count

    return {
        "attempt_id": attempt.id,
        "exam_id": attempt.exam_id,
        "total_mcq_questions": len(exam_questions),
        "answered_questions": answered_count,
        "unanswered_questions": unanswered_count,
        "correct_answers": correct_count,
        "incorrect_answers": incorrect_count,
        "total_marks_possible": round(total_possible, 2),
        "total_marks_obtained": round(total_obtained, 2),
        "breakdown": breakdown,
    }
