from typing import Union
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, get_current_active_user, require_role
from app.models.user import User
from app.schemas.autosave import (
    MCQAutoSaveRequest,
    MCQAutoSaveResponse,
    CodeAutoSaveRequest,
    CodeAutoSaveResponse,
    BatchAutoSaveResponse,
)
from app.services import autosave_service

router = APIRouter(
    prefix="/exam-attempts",
    tags=["Auto-save Engine"],
    dependencies=[Depends(require_role(["student"]))],
)


@router.put(
    "/{attempt_id}/answers/autosave",
    response_model=Union[MCQAutoSaveResponse, BatchAutoSaveResponse],
    status_code=status.HTTP_200_OK,
    summary="Autosave student's MCQ answer or batch answers",
    responses={
        200: {"description": "Answer(s) autosaved successfully"},
        400: {"description": "Attempt inactive, expired, invalid question/option, or mismatch"},
        401: {"description": "Missing or invalid authentication token"},
        403: {"description": "Forbidden - requires Student role or attempt ownership"},
        404: {"description": "Exam attempt or exam not found"},
        409: {"description": "Integrity conflict during autosave"},
    },
)
def autosave_mcq(
    attempt_id: int,
    payload: MCQAutoSaveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Accept periodic partial MCQ answer snapshots without submitting the exam.
    - Validates attempt ownership, active status, and server-authoritative timer.
    - Idempotently creates or updates the student's AttemptAnswer.
    - Never calculates final marks or finalizes the exam.
    - Supports single MCQ answers as well as batch payloads from frontend useAutoSave.
    """
    # Check if this is a batch payload from the frontend hook
    if payload.mcq_answers is not None or payload.coding_drafts is not None:
        batch_result = autosave_service.autosave_batch_payload(
            db=db,
            attempt_id=attempt_id,
            mcq_answers=payload.mcq_answers,
            coding_drafts=payload.coding_drafts,
            current_user=current_user,
        )
        return BatchAutoSaveResponse(**batch_result)

    # Otherwise, handle single MCQ autosave
    if payload.question_id is None:
        return MCQAutoSaveResponse(
            success=True,
            message="No answer provided for autosave",
            attempt_id=attempt_id,
            question_id=None,
            selected_option_id=None,
        )

    answer = autosave_service.autosave_mcq_answer(
        db=db,
        attempt_id=attempt_id,
        question_id=payload.question_id,
        selected_option_id=payload.selected_option_id,
        current_user=current_user,
    )

    return MCQAutoSaveResponse(
        success=True,
        message="Answer autosaved successfully",
        attempt_id=attempt_id,
        question_id=answer.question_id,
        selected_option_id=answer.selected_option_id,
        answered_at=answer.answered_at,
    )


@router.put(
    "/{attempt_id}/coding/{coding_question_id}/autosave",
    response_model=CodeAutoSaveResponse,
    status_code=status.HTTP_200_OK,
    summary="Autosave student's coding source draft",
    responses={
        200: {"description": "Code draft autosaved successfully"},
        400: {"description": "Attempt inactive, expired, invalid question, or disallowed language"},
        401: {"description": "Missing or invalid authentication token"},
        403: {"description": "Forbidden - requires Student role or attempt ownership"},
        404: {"description": "Exam attempt or question not found"},
    },
)
def autosave_coding(
    attempt_id: int,
    coding_question_id: int,
    payload: CodeAutoSaveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Save the student's current source code draft without treating it as a final submission.
    - Saves with is_final = False and status = 'draft'.
    - Updates existing non-final draft idempotently without creating excessive rows.
    - Does NOT execute the code, trigger Judge0, or evaluate test cases.
    - Final submissions (is_final = True) are protected and never modified.
    """
    submission = autosave_service.autosave_code_draft(
        db=db,
        attempt_id=attempt_id,
        coding_question_id=coding_question_id,
        language=payload.language,
        source_code=payload.source_code,
        current_user=current_user,
    )

    return CodeAutoSaveResponse(
        success=True,
        message="Code draft autosaved successfully",
        attempt_id=attempt_id,
        coding_question_id=coding_question_id,
        submission_id=submission.id,
        language=submission.language,
        updated_at=submission.updated_at,
    )
