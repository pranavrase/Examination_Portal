from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, require_role, get_current_active_user
from app.schemas.question import (
    QuestionCategoryCreate,
    QuestionCategoryUpdate,
    QuestionCategoryResponse,
)
from app.services import question_service

router = APIRouter(
    prefix="/question-categories",
    tags=["Question Categories"],
    dependencies=[Depends(require_role(["admin", "examiner"]))],
)


@router.post(
    "",
    response_model=QuestionCategoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new question category (Examiner / Admin)",
)
def create_category(
    cat_in: QuestionCategoryCreate,
    db: Session = Depends(get_db),
):
    """
    Create a new question category with name, topic, and difficulty level.
    """
    return question_service.create_category(db=db, cat_in=cat_in)


@router.get(
    "",
    response_model=List[QuestionCategoryResponse],
    status_code=status.HTTP_200_OK,
    summary="List question categories with optional filtering",
)
def get_categories(
    name: Optional[str] = Query(None, description="Filter by category name substring"),
    topic: Optional[str] = Query(None, description="Filter by topic substring"),
    difficulty: Optional[str] = Query(None, description="Filter by difficulty (easy, medium, hard)"),
    db: Session = Depends(get_db),
):
    """
    Retrieve all question categories matching optional filter criteria.
    """
    return question_service.list_categories(
        db=db,
        name=name,
        topic=topic,
        difficulty=difficulty,
    )


@router.get(
    "/{category_id}",
    response_model=QuestionCategoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get question category by ID",
)
def get_category(
    category_id: int,
    db: Session = Depends(get_db),
):
    """
    Retrieve single question category details by ID.
    """
    return question_service.get_category_by_id(db=db, category_id=category_id)


@router.put(
    "/{category_id}",
    response_model=QuestionCategoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Update question category",
)
def update_category(
    category_id: int,
    cat_in: QuestionCategoryUpdate,
    db: Session = Depends(get_db),
):
    """
    Update question category name, topic, or difficulty.
    """
    return question_service.update_category(db=db, category_id=category_id, cat_in=cat_in)


@router.delete(
    "/{category_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete question category",
)
def delete_category(
    category_id: int,
    db: Session = Depends(get_db),
):
    """
    Delete a question category if no questions depend on it.
    """
    question_service.delete_category(db=db, category_id=category_id)
    return {
        "message": f"Question category with ID {category_id} deleted successfully",
        "id": category_id,
    }
