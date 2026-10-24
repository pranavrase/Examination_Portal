from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, get_current_active_user
from app.models.user import User
from app.schemas.mcq import (
    MCQExamQuestionsResponse,
    MCQAnswerCreate,
    MCQAnswerUpdate,
    MCQAnswerResponse,
    MCQAttemptAnswersResponse,
    MCQScoreResponse,
)
from app.services import mcq_service

router = APIRouter(
    prefix="/mcq",
    tags=["MCQ Exam Engine"],
)


@router.get(
    "/exams/{exam_id}/questions",
    response_model=MCQExamQuestionsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get randomized MCQ questions for an exam attempt",
)
def get_exam_mcq_questions(
    exam_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Retrieve all MCQ questions for the student's exam attempt.
    - Applies question randomization per attempt seed if configured.
    - Applies option randomization per attempt+question seed if configured.
    - Excludes coding questions.
    - Anti-leak: NEVER exposes is_correct.
    - Returns student's previously selected option if already answered.
    """
    return mcq_service.generate_randomized_question_set(
        db=db,
        exam_id=exam_id,
        current_user=current_user,
    )


@router.post(
    "/attempts/{attempt_id}/answers",
    response_model=MCQAnswerResponse,
    status_code=status.HTTP_200_OK,
    summary="Record or update an MCQ answer",
)
def submit_mcq_answer(
    attempt_id: int,
    answer_in: MCQAnswerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Record or update a student's answer to an MCQ question.
    - Server-side validates question mapping, option ownership, and correctness.
    - Calculates marks awarded and negative marks.
    - Enforces uniqueness on (attempt_id, question_id).
    """
    answer = mcq_service.record_mcq_answer(
        db=db,
        attempt_id=attempt_id,
        question_id=answer_in.question_id,
        selected_option_id=answer_in.selected_option_id,
        current_user=current_user,
    )
    return MCQAnswerResponse(
        attempt_id=answer.attempt_id,
        question_id=answer.question_id,
        selected_option_id=answer.selected_option_id,
        answered_at=answer.answered_at,
        message="Answer recorded successfully",
    )


@router.put(
    "/attempts/{attempt_id}/answers/{question_id}",
    response_model=MCQAnswerResponse,
    status_code=status.HTTP_200_OK,
    summary="Update an existing MCQ answer",
)
def update_mcq_answer(
    attempt_id: int,
    question_id: int,
    answer_in: MCQAnswerUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Change or update a previously selected option for an MCQ question in an active attempt.
    """
    answer = mcq_service.record_mcq_answer(
        db=db,
        attempt_id=attempt_id,
        question_id=question_id,
        selected_option_id=answer_in.selected_option_id,
        current_user=current_user,
    )
    return MCQAnswerResponse(
        attempt_id=answer.attempt_id,
        question_id=answer.question_id,
        selected_option_id=answer.selected_option_id,
        answered_at=answer.answered_at,
        message="Answer updated successfully",
    )


@router.get(
    "/attempts/{attempt_id}/answers",
    response_model=MCQAttemptAnswersResponse,
    status_code=status.HTTP_200_OK,
    summary="Get all recorded answers for an attempt",
)
def get_attempt_answers(
    attempt_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Retrieve all recorded answers for the authenticated student's attempt.
    """
    return mcq_service.get_attempt_answers(
        db=db,
        attempt_id=attempt_id,
        current_user=current_user,
    )


@router.post(
    "/attempts/{attempt_id}/score",
    response_model=MCQScoreResponse,
    status_code=status.HTTP_200_OK,
    summary="Score MCQ responses for an attempt",
)
def score_attempt(
    attempt_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Calculate and return the MCQ scoring breakdown and total marks obtained for an attempt.
    """
    return mcq_service.score_attempt_mcqs(
        db=db,
        attempt_id=attempt_id,
        current_user=current_user,
    )
