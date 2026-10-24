from pydantic import BaseModel, Field, ConfigDict


class RoleResponse(BaseModel):
    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)


class CreateRoleRequest(BaseModel):
    name: str = Field(..., min_length=2, description="Unique role name e.g. admin, examiner, student")


class AssignRoleRequest(BaseModel):
    role_name: str = Field(..., min_length=2, description="Role name to assign")
