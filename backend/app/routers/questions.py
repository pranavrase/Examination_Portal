from typing import List, Optional, Union
from pydantic import BaseModel
from fastapi import APIRouter, Depends, Query, UploadFile, File, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, require_role, get_current_active_user
from app.models.user import User
from app.schemas.question import (
    QuestionCreate,
    QuestionUpdate,
    QuestionResponse,
    QuestionDetailResponse,
    QuestionListResponse,
    CodingTestCaseCreate,
    CodingTestCaseUpdate,
    CodingTestCaseResponse,
    BulkImportResponse,
)
from app.services import question_service

router = APIRouter(
    prefix="/questions",
    tags=["Question Bank"],
    dependencies=[Depends(require_role(["admin", "examiner"]))],
)


@router.post(
    "",
    response_model=QuestionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new MCQ or Coding question (Examiner / Admin)",
)
def create_question(
    q_in: QuestionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Create a new question in the Question Bank.
    Accepts either an MCQ question with options or a Coding question with problem statement and limits.
    """
    return question_service.create_question(
        db=db,
        q_in=q_in,
        creator_id=current_user.id,
    )


@router.get(
    "",
    response_model=QuestionListResponse,
    status_code=status.HTTP_200_OK,
    summary="List questions with filtering and pagination",
)
def list_questions(
    category: Optional[str] = Query(None, description="Filter by category name"),
    topic: Optional[str] = Query(None, description="Filter by topic name"),
    difficulty: Optional[str] = Query(None, description="Filter by difficulty (easy, medium, hard)"),
    question_type: Optional[str] = Query(None, description="Filter by question type (mcq, coding)"),
    created_by: Optional[int] = Query(None, description="Filter by creator user ID"),
    search: Optional[str] = Query(None, description="Search question text keyword"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Retrieve questions matching filter criteria with pagination.
    """
    return question_service.list_questions_by_filter(
        db=db,
        current_user=current_user,
        category=category,
        topic=topic,
        difficulty=difficulty,
        question_type=question_type,
        created_by=created_by,
        search=search,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{question_id}",
    response_model=QuestionDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get question details by ID",
)
def get_question(
    question_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Retrieve detailed question data including options or coding metadata and test cases.
    """
    return question_service.get_question_by_id(
        db=db,
        question_id=question_id,
        current_user=current_user,
    )


@router.put(
    "/{question_id}",
    response_model=QuestionResponse,
    status_code=status.HTTP_200_OK,
    summary="Update question",
)
def update_question(
    question_id: int,
    q_in: QuestionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Update question text, marks, category, options, or coding details.
    Enforces ownership validation.
    """
    return question_service.update_question(
        db=db,
        question_id=question_id,
        q_in=q_in,
        current_user=current_user,
    )


@router.delete(
    "/{question_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete question",
)
def delete_question(
    question_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Delete a question and its associated options or test cases.
    Enforces ownership and ensures question is not mapped to active exams.
    """
    question_service.delete_question(
        db=db,
        question_id=question_id,
        current_user=current_user,
    )
    return {
        "message": f"Question with ID {question_id} deleted successfully",
        "id": question_id,
    }


# ---------------------------------------------------------------------------
# Coding Test Cases Endpoints
# ---------------------------------------------------------------------------

class TestCasesContainer(BaseModel):
    test_cases: List[CodingTestCaseCreate]


@router.post(
    "/coding/{question_id}/test-cases",
    response_model=List[CodingTestCaseResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Add test cases to a coding question",
)
def add_test_cases(
    question_id: int,
    test_cases: Union[List[CodingTestCaseCreate], TestCasesContainer],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Add one or multiple test cases (sample or hidden) to a coding question.
    Accepts either a JSON array of test cases or an object with { test_cases: [...] }.
    """
    actual_list = test_cases.test_cases if isinstance(test_cases, TestCasesContainer) else test_cases
    return question_service.add_test_cases(
        db=db,
        question_id=question_id,
        test_cases_in=actual_list,
        current_user=current_user,
    )


@router.put(
    "/coding/{question_id}/test-cases/{test_case_id}",
    response_model=CodingTestCaseResponse,
    status_code=status.HTTP_200_OK,
    summary="Update a coding test case",
)
def update_test_case(
    question_id: int,
    test_case_id: int,
    tc_in: CodingTestCaseUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Update input, expected output, or sample/hidden status of a test case.
    """
    return question_service.update_test_case(
        db=db,
        question_id=question_id,
        test_case_id=test_case_id,
        tc_in=tc_in,
        current_user=current_user,
    )


@router.delete(
    "/coding/{question_id}/test-cases/{test_case_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a coding test case",
)
def delete_test_case(
    question_id: int,
    test_case_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Delete a specific test case from a coding question.
    """
    question_service.delete_test_case(
        db=db,
        question_id=question_id,
        test_case_id=test_case_id,
        current_user=current_user,
    )
    return {
        "message": f"Test case {test_case_id} successfully deleted from question {question_id}",
        "question_id": question_id,
        "test_case_id": test_case_id,
    }


# ---------------------------------------------------------------------------
# Bulk Import Endpoint
# ---------------------------------------------------------------------------

@router.post(
    "/bulk-import",
    response_model=BulkImportResponse,
    status_code=status.HTTP_200_OK,
    summary="Bulk import questions from CSV",
)
@router.post(
    "/import",
    response_model=BulkImportResponse,
    status_code=status.HTTP_200_OK,
    summary="Bulk import questions from CSV (Alias for /bulk-import)",
)
async def bulk_import(
    file: UploadFile = File(..., description="CSV file containing questions to import"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Upload and parse a CSV file to import multiple MCQ and Coding questions in bulk.
    """
    content = await file.read()
    return question_service.bulk_import_questions(
        db=db,
        file_content=content,
        filename=file.filename or "questions.csv",
        creator_id=current_user.id,
    )
