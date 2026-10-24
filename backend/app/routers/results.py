"""
Module 2.10 — Results Router
==============================
Endpoints:
  GET  /results/{attempt_id}           — student (own), examiner/admin
  GET  /results/{attempt_id}/breakdown — detailed score breakdown
  GET  /exams/{exam_id}/results        — examiner/admin: all results for an exam
  POST /results/{attempt_id}/calculate — admin/examiner: trigger re-calculation
"""

from typing import List
from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.core.dependencies import get_db, get_current_active_user, require_role
from app.models.user import User
from app.models.attempt import ExamAttempt, AttemptAnswer, CodingSubmission
from app.models.question import Question, McqOption, CodingQuestion, ExamQuestion
from app.models.exam import Exam
from app.models.result import Result
from app.schemas.result import (
    ResultResponse,
    ResultSummaryResponse,
    ResultListItem,
    ScoreBreakdown,
    MCQBreakdownItem,
    CodingBreakdownItem,
)
from app.services import result_service

router = APIRouter(tags=["Results — Module 2.10"])


# ---------------------------------------------------------------------------
# Helper: build ResultResponse from ORM objects
# ---------------------------------------------------------------------------

def _build_result_response(
    result: Result,
    attempt: ExamAttempt,
    breakdown: ScoreBreakdown | None = None,
) -> ResultResponse:
    return ResultResponse(
        attempt_id=result.attempt_id,
        exam_id=attempt.exam_id,
        student_id=attempt.student_id,
        total_marks_obtained=float(result.total_marks_obtained),
        total_marks_possible=float(result.total_marks_possible),
        percentage=float(result.percentage),
        pass_fail=result.pass_fail,
        calculated_at=result.calculated_at,
        breakdown=breakdown,
    )


def _build_breakdown(db: Session, attempt: ExamAttempt) -> ScoreBreakdown:
    """Build a ScoreBreakdown from persisted data (no re-calculation)."""
    exam_questions: list[ExamQuestion] = (
        db.query(ExamQuestion)
        .filter(ExamQuestion.exam_id == attempt.exam_id)
        .all()
    )

    q_ids = [eq.question_id for eq in exam_questions]
    questions = (
        db.query(Question)
        .options(joinedload(Question.mcq_options), joinedload(Question.coding_details))
        .filter(Question.id.in_(q_ids))
        .all()
    ) if q_ids else []
    q_map = {q.id: q for q in questions}

    answers: list[AttemptAnswer] = (
        db.query(AttemptAnswer)
        .filter(AttemptAnswer.attempt_id == attempt.id)
        .all()
    )
    ans_map = {a.question_id: a for a in answers}

    mcq_eqs = [eq for eq in exam_questions if q_map.get(eq.question_id) and q_map[eq.question_id].question_type == "mcq"]
    coding_eqs = [eq for eq in exam_questions if q_map.get(eq.question_id) and q_map[eq.question_id].question_type == "coding"]

    # MCQ
    mcq_possible = 0.0
    mcq_obtained = 0.0
    mcq_items: list[MCQBreakdownItem] = []

    for eq in mcq_eqs:
        em = float(eq.marks_override) if eq.marks_override is not None else float(q_map[eq.question_id].marks)
        mcq_possible += em
        ans = ans_map.get(eq.question_id)
        awarded = float(ans.marks_awarded) if (ans and ans.marks_awarded is not None) else 0.0
        mcq_obtained += awarded
        mcq_items.append(MCQBreakdownItem(
            question_id=eq.question_id,
            effective_marks=em,
            marks_awarded=awarded,
            is_correct=ans.is_correct if ans else None,
            answered=ans is not None and ans.selected_option_id is not None,
        ))

    # Coding
    coding_possible = 0.0
    coding_obtained = 0.0
    coding_items: list[CodingBreakdownItem] = []

    for eq in coding_eqs:
        em = float(eq.marks_override) if eq.marks_override is not None else float(q_map[eq.question_id].marks)
        coding_possible += em
        q = q_map[eq.question_id]
        cq: CodingQuestion | None = q.coding_details
        best_sub = None
        best_awarded = 0.0
        if cq:
            subs = (
                db.query(CodingSubmission)
                .options(joinedload(CodingSubmission.execution_results))
                .filter(
                    CodingSubmission.attempt_id == attempt.id,
                    CodingSubmission.coding_question_id == cq.id,
                )
                .all()
            )
            for sub in subs:
                score = 0.0
                if sub.execution_results:
                    tot = len(sub.execution_results)
                    passed = sum(1 for r in sub.execution_results if r.verdict == "passed")
                    if tot > 0:
                        score = round((passed / tot) * em, 2)
                if sub.score is not None and float(sub.score) > score:
                    score = float(sub.score)
                if score > best_awarded or best_sub is None:
                    best_awarded = score
                    best_sub = sub

        awarded = min(best_awarded, em)  # cap
        coding_obtained += awarded
        coding_items.append(CodingBreakdownItem(
            question_id=eq.question_id,
            coding_question_id=cq.id if cq else None,
            effective_marks=em,
            marks_awarded=round(awarded, 2),
            submission_status=best_sub.status if best_sub else None,
        ))

    # Negative marks = mcq_possible - (mcq_obtained + correct_marks)
    # Simpler: sum of penalties = sum of absolute values of negative marks_awarded
    neg_applied = sum(
        abs(float(a.marks_awarded))
        for a in answers
        if a.marks_awarded is not None and float(a.marks_awarded) < 0
    )

    return ScoreBreakdown(
        mcq_marks_obtained=round(mcq_obtained, 2),
        mcq_marks_possible=round(mcq_possible, 2),
        coding_marks_obtained=round(coding_obtained, 2),
        coding_marks_possible=round(coding_possible, 2),
        negative_marks_applied=round(neg_applied, 2),
        mcq_breakdown=mcq_items,
        coding_breakdown=coding_items,
    )


# ---------------------------------------------------------------------------
# GET /results/{attempt_id}
# ---------------------------------------------------------------------------

@router.get(
    "/results/{attempt_id}",
    response_model=ResultResponse,
    status_code=status.HTTP_200_OK,
    summary="Get the final result for an exam attempt",
    responses={
        200: {"description": "Result returned successfully"},
        401: {"description": "Missing or invalid JWT token"},
        403: {"description": "Forbidden — students may only access their own result"},
        404: {"description": "Attempt or result not found"},
        409: {"description": "Attempt still in_progress — no final result yet"},
    },
)
def get_result(
    attempt_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Return the final exam result.

    Authorization:
    - **Student** → own attempt only
    - **Examiner** → attempts for exams they created
    - **Admin** → all attempts
    """
    result, attempt = result_service.get_result_for_student(
        db=db,
        attempt_id=attempt_id,
        current_user=current_user,
    )
    return _build_result_response(result, attempt)


# ---------------------------------------------------------------------------
# GET /results/{attempt_id}/breakdown
# ---------------------------------------------------------------------------

@router.get(
    "/results/{attempt_id}/breakdown",
    response_model=ResultResponse,
    status_code=status.HTTP_200_OK,
    summary="Get the full score breakdown for an exam attempt",
    responses={
        200: {"description": "Result with question-level breakdown returned"},
        401: {"description": "Missing or invalid JWT token"},
        403: {"description": "Forbidden"},
        404: {"description": "Attempt or result not found"},
    },
)
def get_result_with_breakdown(
    attempt_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Return the exam result including per-question score breakdown.
    Correct answers are **never** exposed.

    Authorization:
    - **Student** → own attempt only
    - **Examiner** → their exams
    - **Admin** → all
    """
    result, attempt = result_service.get_result_for_student(
        db=db,
        attempt_id=attempt_id,
        current_user=current_user,
    )
    breakdown = _build_breakdown(db=db, attempt=attempt)
    return _build_result_response(result, attempt, breakdown=breakdown)


# ---------------------------------------------------------------------------
# GET /exams/{exam_id}/results  — examiner/admin only
# ---------------------------------------------------------------------------

@router.get(
    "/exams/{exam_id}/results",
    response_model=List[ResultListItem],
    status_code=status.HTTP_200_OK,
    summary="List all results for an exam (Examiner / Admin)",
    dependencies=[Depends(require_role(["admin", "examiner"]))],
    responses={
        200: {"description": "List of result records for the exam"},
        401: {"description": "Missing or invalid JWT token"},
        403: {"description": "Forbidden — examiners may only see their own exams"},
        404: {"description": "Exam not found"},
    },
)
def list_exam_results(
    exam_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Return all final results for a given exam.

    Authorization:
    - **Examiner** → their own exams only
    - **Admin** → all exams
    """
    pairs = result_service.get_results_for_exam(
        db=db,
        exam_id=exam_id,
        current_user=current_user,
    )

    items = []
    for res, att in pairs:
        student = att.student if att.student else db.query(User).filter(User.id == att.student_id).first()

        items.append(ResultListItem(
            attempt_id=res.attempt_id,
            exam_id=att.exam_id,
            student_id=att.student_id,
            student_email=student.email if student else None,
            student_name=student.full_name if student else None,
            total_marks_obtained=float(res.total_marks_obtained),
            total_marks_possible=float(res.total_marks_possible),
            percentage=float(res.percentage),
            pass_fail=res.pass_fail,
            calculated_at=res.calculated_at,
        ))

    return items


# ---------------------------------------------------------------------------
# POST /results/{attempt_id}/calculate  — admin/examiner: re-trigger scoring
# ---------------------------------------------------------------------------

@router.post(
    "/results/{attempt_id}/calculate",
    response_model=ResultSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="(Re-)calculate result for a submitted attempt (Admin / Examiner)",
    dependencies=[Depends(require_role(["admin", "examiner"]))],
    responses={
        200: {"description": "Result calculated and stored"},
        401: {"description": "Missing or invalid JWT token"},
        403: {"description": "Forbidden"},
        404: {"description": "Attempt not found"},
        409: {"description": "Attempt still in_progress — must be submitted first"},
    },
)
def recalculate_result(
    attempt_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Trigger (or re-trigger) result calculation for a finalized attempt.
    Safe to call multiple times — idempotent.

    Authorization: **Admin** or **Examiner** only.
    """
    result = result_service.calculate_final_score(db=db, attempt_id=attempt_id)
    return ResultSummaryResponse(
        attempt_id=result.attempt_id,
        total_marks_obtained=float(result.total_marks_obtained),
        total_marks_possible=float(result.total_marks_possible),
        percentage=float(result.percentage),
        pass_fail=result.pass_fail,
        calculated_at=result.calculated_at,
    )
