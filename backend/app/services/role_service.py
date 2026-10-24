from typing import List
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.role import Role, UserRole
from app.models.user import User
from app.schemas.role import CreateRoleRequest
from app.core.config import settings
from app.core.security import hash_password


SYSTEM_ROLES = {"admin", "examiner", "student"}


def seed_default_roles(db: Session) -> None:
    """Ensures standard system default roles exist in the database."""
    default_role_names = ["admin", "examiner", "student"]

    for name in default_role_names:
        existing = db.query(Role).filter(Role.name == name).first()
        if not existing:
            new_role = Role(name=name)
            db.add(new_role)
    db.commit()


def seed_admin_account(db: Session) -> None:
    """
    Ensures the default secure administrator account exists:
    - Email: examinationportal26@gmail.com
    - Password hashed from settings.ADMIN_PASSWORD
    - Assigned role 'admin'
    """
    admin_email = "examinationportal26@gmail.com"
    admin_password = settings.ADMIN_PASSWORD or "Admin@12345"

    admin_role = db.query(Role).filter(Role.name == "admin").first()
    if not admin_role:
        admin_role = Role(name="admin")
        db.add(admin_role)
        db.commit()
        db.refresh(admin_role)

    user = db.query(User).filter(User.email == admin_email).first()
    if not user:
        user = User(
            email=admin_email,
            full_name="System Administrator",
            password_hash=hash_password(admin_password),
            role="admin",
            is_active=True,
            is_verified=True,
        )
        user.roles.append(admin_role)
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        if admin_role not in user.roles:
            user.roles.append(admin_role)
        user.role = "admin"
        user.is_active = True
        db.commit()


def list_roles(db: Session) -> List[Role]:
    """Retrieves all defined roles."""
    return db.query(Role).all()


def create_role(db: Session, role_in: CreateRoleRequest) -> Role:
    """Creates a new role."""
    normalized_name = role_in.name.lower().strip()
    
    existing = db.query(Role).filter(Role.name == normalized_name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Role '{normalized_name}' already exists"
        )

    role = Role(name=normalized_name)
    db.add(role)
    db.commit()
    db.refresh(role)
    return role


def delete_role(db: Session, role_id: int) -> None:
    """Deletes a custom role by ID. Prevents deletion of system default roles."""
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Role with ID {role_id} not found"
        )

    if role.name in SYSTEM_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"System role '{role.name}' cannot be deleted"
        )

    db.delete(role)
    db.commit()


def assign_role_to_user(db: Session, user_id: int, role_name: str) -> User:
    """Assigns a role to a user, ensuring no duplicate relationship."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )

    normalized_role_name = role_name.lower().strip()
    role = db.query(Role).filter(Role.name == normalized_role_name).first()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Role '{normalized_role_name}' not found"
        )

    if role in user.roles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User already has role '{normalized_role_name}' assigned"
        )

    user.roles.append(role)
    db.commit()
    db.refresh(user)
    return user


def remove_role_from_user(db: Session, user_id: int, role_name: str) -> User:
    """Removes a role from a user. Prevents removing the last admin role."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )

    normalized_role_name = role_name.lower().strip()
    role = db.query(Role).filter(Role.name == normalized_role_name).first()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Role '{normalized_role_name}' not found"
        )

    if role not in user.roles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User does not possess role '{normalized_role_name}'"
        )

    # Protect last remaining admin
    if normalized_role_name == "admin":
        admin_count = (
            db.query(User)
            .filter(User.is_active == True)
            .filter(User.roles.any(Role.name == "admin"))
            .count()
        )
        if admin_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot remove the final admin role from the system"
            )

    user.roles.remove(role)
    db.commit()
    db.refresh(user)
    return user
