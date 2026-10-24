from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, require_role, get_current_active_user
from app.core.security import hash_password
from app.models.user import User
from app.models.role import Role
from app.models.exam import Exam
from app.models.question import Question
from app.schemas.user import UserResponse


router = APIRouter(
    prefix="/admin",
    tags=["Admin Management"],
    dependencies=[Depends(require_role("admin"))]
)


class ExaminerCreateRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6, description="Password for examiner account")
    full_name: str = Field(..., min_length=2, description="Full name of examiner")


@router.post(
    "/examiners",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new Examiner account (Admin only)"
)
def create_examiner(
    examiner_in: ExaminerCreateRequest,
    db: Session = Depends(get_db)
):
    """
    Creates a new examiner account.
    - Restricted to Admin role only.
    - Validates uniqueness of email.
    - Hashes password using bcrypt.
    - Assigns examiner role.
    """
    normalized_email = examiner_in.email.lower().strip()

    existing_user = db.query(User).filter(User.email == normalized_email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email address is already registered"
        )

    examiner_role = db.query(Role).filter(Role.name == "examiner").first()
    if not examiner_role:
        examiner_role = Role(name="examiner")
        db.add(examiner_role)
        db.commit()
        db.refresh(examiner_role)

    user = User(
        email=normalized_email,
        full_name=examiner_in.full_name.strip(),
        password_hash=hash_password(examiner_in.password),
        role="examiner",
        is_active=True,
        is_verified=True,
    )
    user.roles.append(examiner_role)

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


@router.delete(
    "/examiners/{user_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete an Examiner account (Admin only)"
)
def delete_examiner(
    user_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Deletes an existing examiner account.
    - Restricted to Admin role only.
    - Prevents admins from deleting their own account.
    - Prevents deleting admin accounts.
    - Checks for referenced authored exams and questions to prevent foreign key errors.
    """
    # Prevent self-deletion
    if current_user.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Administrators cannot delete their own account"
        )

    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )

    # Protect administrator accounts from deletion
    if target_user.email == "examinationportal26@gmail.com" or any(r.name == "admin" for r in target_user.roles):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Administrator accounts cannot be deleted"
        )

    # Ensure target user is indeed an examiner
    is_examiner = any(r.name == "examiner" for r in target_user.roles) or target_user.role == "examiner"
    if not is_examiner:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Target user is not an examiner"
        )

    # Check for foreign key constraints on authored exams / questions
    has_exams = db.query(Exam).filter(Exam.created_by == user_id).first() is not None
    has_questions = db.query(Question).filter(Question.created_by == user_id).first() is not None
    if has_exams or has_questions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete examiner account because they have authored exams or questions. Deactivate the account instead."
        )

    deleted_email = target_user.email
    db.delete(target_user)
    db.commit()

    return {"message": f"Examiner account '{deleted_email}' deleted successfully"}
