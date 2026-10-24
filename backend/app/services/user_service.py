from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import or_
from fastapi import HTTPException, status

from app.models.user import User
from app.models.role import Role
from app.models.activity import LoginSession
from app.schemas.user import UserListResponse, UserResponse


def list_users(
    db: Session,
    page: int = 1,
    page_size: int = 20,
    email: Optional[str] = None,
    full_name: Optional[str] = None,
    role: Optional[str] = None,
    is_active: Optional[bool] = None
) -> UserListResponse:
    """
    Retrieves a paginated list of users with optional filtering parameters.
    """
    if page < 1:
        page = 1
    if page_size < 1:
        page_size = 20
    if page_size > 100:
        page_size = 100

    query = db.query(User)

    if email:
        query = query.filter(User.email.ilike(f"%{email.strip()}%"))

    if full_name:
        query = query.filter(User.full_name.ilike(f"%{full_name.strip()}%"))

    if role:
        target_role = role.lower().strip()
        query = query.filter(
            User.roles.any(Role.name == target_role)
        )

    if is_active is not None:
        query = query.filter(User.is_active == is_active)

    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()

    items_response = [UserResponse.model_validate(u) for u in items]

    return UserListResponse(
        items=items_response,
        page=page,
        page_size=page_size,
        total=total
    )


def get_user_by_id(db: Session, user_id: int) -> User:
    """Retrieves single user details by ID."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )
    return user


def update_user_role(db: Session, user_id: int, role_name: str) -> User:
    """Assigns or updates a user's primary role."""
    user = get_user_by_id(db, user_id)
    normalized_role = role_name.lower().strip()

    role_obj = db.query(Role).filter(Role.name == normalized_role).first()
    if not role_obj:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid or non-existent role '{normalized_role}'"
        )

    # Set as primary role
    user.roles = [role_obj]

    db.commit()
    db.refresh(user)
    return user


def deactivate_user(db: Session, user_id: int) -> User:
    """
    Deactivates a user account (is_active = False).
    Does not delete the user record permanently.
    Prevents deactivating the final active admin account.
    """
    user = get_user_by_id(db, user_id)

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User account is already inactive"
        )

    # Prevent deactivating the last active admin
    is_admin = any(r.name == "admin" for r in user.roles)
    if is_admin:
        active_admins = (
            db.query(User)
            .filter(User.is_active == True)
            .filter(User.roles.any(Role.name == "admin"))
            .count()
        )
        if active_admins <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot deactivate the final active administrator account"
            )

    user.is_active = False

    # Deactivate active sessions
    active_sessions = db.query(LoginSession).filter(
        LoginSession.user_id == user.id,
        LoginSession.is_active == True
    ).all()
    for session in active_sessions:
        session.is_active = False

    db.commit()
    db.refresh(user)
    return user
