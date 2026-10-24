from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, require_role
from app.schemas.role import RoleResponse, CreateRoleRequest
from app.schemas.auth import MessageResponse
from app.services import role_service

router = APIRouter(
    prefix="/roles",
    tags=["Role Management"],
    dependencies=[Depends(require_role("admin"))]
)


@router.get(
    "",
    response_model=List[RoleResponse],
    status_code=status.HTTP_200_OK,
    summary="List all available roles (Admin only)"
)
def get_roles(db: Session = Depends(get_db)):
    """Retrieve list of all roles in the system."""
    return role_service.list_roles(db=db)


@router.post(
    "",
    response_model=RoleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a custom role (Admin only)"
)
def create_new_role(
    role_in: CreateRoleRequest,
    db: Session = Depends(get_db)
):
    """Create a new custom user role."""
    return role_service.create_role(db=db, role_in=role_in)


@router.delete(
    "/{role_id}",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete custom role by ID (Admin only)"
)
def delete_existing_role(
    role_id: int,
    db: Session = Depends(get_db)
):
    """Delete a custom role. System default roles cannot be deleted."""
    role_service.delete_role(db=db, role_id=role_id)
    return MessageResponse(message=f"Role with ID {role_id} successfully deleted")
