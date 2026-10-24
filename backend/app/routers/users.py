from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, require_role
from app.schemas.user import UserResponse, UserListResponse, UpdateUserRoleRequest
from app.schemas.role import AssignRoleRequest
from app.services import user_service, role_service

router = APIRouter(
    prefix="/users",
    tags=["User Management"],
    dependencies=[Depends(require_role("admin"))]
)


@router.get(
    "",
    response_model=UserListResponse,
    status_code=status.HTTP_200_OK,
    summary="List users with pagination and filtering (Admin only)"
)
def get_users(
    page: int = Query(1, ge=1, description="Page number starting from 1"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    email: Optional[str] = Query(None, description="Filter by email substring"),
    full_name: Optional[str] = Query(None, description="Filter by full name substring"),
    role: Optional[str] = Query(None, description="Filter by role name"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    db: Session = Depends(get_db)
):
    """Retrieve a paginated list of users with optional filtering."""
    return user_service.list_users(
        db=db,
        page=page,
        page_size=page_size,
        email=email,
        full_name=full_name,
        role=role,
        is_active=is_active
    )


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get user details by ID (Admin only)"
)
def get_user(
    user_id: int,
    db: Session = Depends(get_db)
):
    """Retrieve detailed information for a single user by ID."""
    return user_service.get_user_by_id(db=db, user_id=user_id)


@router.put(
    "/{user_id}/role",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Assign or update a user's role (Admin only)"
)
def update_role(
    user_id: int,
    role_in: UpdateUserRoleRequest,
    db: Session = Depends(get_db)
):
    """Update a user's primary role."""
    return user_service.update_user_role(db=db, user_id=user_id, role_name=role_in.role)


@router.delete(
    "/{user_id}",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Deactivate a user account (Admin only)"
)
def deactivate(
    user_id: int,
    db: Session = Depends(get_db)
):
    """Deactivate a user account (sets is_active = False). Does not delete record."""
    return user_service.deactivate_user(db=db, user_id=user_id)


@router.post(
    "/{user_id}/roles",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Assign an additional role to user (Admin only)"
)
def add_user_role(
    user_id: int,
    req: AssignRoleRequest,
    db: Session = Depends(get_db)
):
    """Assign an additional role to a user without duplicate relationships."""
    return role_service.assign_role_to_user(db=db, user_id=user_id, role_name=req.role_name)


@router.delete(
    "/{user_id}/roles/{role_name}",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Remove a role from user (Admin only)"
)
def remove_user_role(
    user_id: int,
    role_name: str,
    db: Session = Depends(get_db)
):
    """Remove a role from a user."""
    return role_service.remove_role_from_user(db=db, user_id=user_id, role_name=role_name)
