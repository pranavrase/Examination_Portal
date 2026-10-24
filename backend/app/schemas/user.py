from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from app.schemas.role import RoleResponse


class UserResponse(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    role: str
    roles: List[RoleResponse] = []
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserListResponse(BaseModel):
    items: List[UserResponse]
    page: int
    page_size: int
    total: int


class UpdateUserRoleRequest(BaseModel):
    role: str = Field(..., min_length=2, description="Target role name: admin, examiner, student")
