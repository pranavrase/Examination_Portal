from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict, model_validator


# ---------------------------------------------------------------------------
# Exam Settings Schemas
# ---------------------------------------------------------------------------

class ExamSettingsBase(BaseModel):
    duration_minutes: int = Field(..., gt=0, description="Duration of the exam in minutes (must be > 0)")
    total_marks: float = Field(..., gt=0, description="Total marks for the exam (must be > 0)")
    passing_percentage: float = Field(..., ge=0, le=100, description="Passing percentage between 0 and 100")
    negative_marking_ratio: float = Field(default=0.0, ge=0, description="Negative marking ratio (e.g. 0.25, must be >= 0)")
    randomize_questions: bool = Field(default=False, description="Whether to randomize question order")
    randomize_options: bool = Field(default=False, description="Whether to randomize option order")


class ExamSettingsCreate(ExamSettingsBase):
    pass


class ExamSettingsUpdate(BaseModel):
    duration_minutes: Optional[int] = Field(None, gt=0, description="Duration in minutes (must be > 0)")
    total_marks: Optional[float] = Field(None, gt=0, description="Total marks (must be > 0)")
    passing_percentage: Optional[float] = Field(None, ge=0, le=100, description="Passing percentage (0 to 100)")
    negative_marking_ratio: Optional[float] = Field(None, ge=0, description="Negative marking ratio (>= 0)")
    randomize_questions: Optional[bool] = None
    randomize_options: Optional[bool] = None


class ExamSettingsResponse(ExamSettingsBase):
    id: int
    exam_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Exam Schemas
# ---------------------------------------------------------------------------

class ExamCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255, description="Exam title cannot be empty")
    description: Optional[str] = Field(None, description="Optional exam description")
    instructions: Optional[str] = Field(None, description="Optional candidate guidelines and instructions")
    status: Optional[str] = Field(default="draft", description="Initial exam status: draft or published")
    assign_all_students: Optional[bool] = Field(default=False, description="Whether to automatically assign all active students upon creation")
    settings: ExamSettingsCreate

    @model_validator(mode="after")
    def validate_title_non_empty(self):
        if not self.title.strip():
            raise ValueError("Exam title cannot be blank")
        return self


class ExamUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255, description="Updated exam title")
    description: Optional[str] = Field(None, description="Updated exam description")
    instructions: Optional[str] = Field(None, description="Updated candidate instructions")
    status: Optional[str] = Field(None, description="Updated exam status: draft, published, or closed")
    assign_all_students: Optional[bool] = Field(default=None, description="Whether to assign all active students")
    settings: Optional[ExamSettingsUpdate] = Field(None, description="Updated exam settings")

    @model_validator(mode="after")
    def validate_title_non_empty(self):
        if self.title is not None and not self.title.strip():
            raise ValueError("Exam title cannot be blank")
        return self


class ExamResponse(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    instructions: Optional[str] = None
    created_by: int
    status: str
    settings: Optional[ExamSettingsResponse] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ExamDetailResponse(ExamResponse):
    total_assigned_students: int = 0


class ExamListResponse(BaseModel):
    items: List[ExamResponse]
    page: int
    page_size: int
    total: int


# ---------------------------------------------------------------------------
# Exam Assignment Schemas
# ---------------------------------------------------------------------------

class ExamAssignmentCreate(BaseModel):
    student_ids: Optional[List[int]] = Field(None, description="List of student user IDs to assign")
    student_id: Optional[int] = Field(None, description="Single student user ID to assign")
    scheduled_start: Optional[datetime] = Field(None, description="Scheduled start time")
    scheduled_end: Optional[datetime] = Field(None, description="Scheduled end time")

    @model_validator(mode="after")
    def validate_assignment_payload(self):
        # Validate that at least one student ID is provided
        ids = []
        if self.student_ids:
            ids.extend(self.student_ids)
        if self.student_id is not None:
            ids.append(self.student_id)

        if not ids:
            raise ValueError("At least one student ID must be provided in 'student_id' or 'student_ids'")

        # Validate schedule window
        if self.scheduled_start and self.scheduled_end:
            if self.scheduled_end <= self.scheduled_start:
                raise ValueError("Scheduled end time must be strictly after scheduled start time")

        return self


class ExamAssignmentResponse(BaseModel):
    id: int
    exam_id: int
    student_id: int
    assigned_at: datetime
    scheduled_start: Optional[datetime] = None
    scheduled_end: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ExamAssignmentListResponse(BaseModel):
    items: List[ExamAssignmentResponse]
    page: int
    page_size: int
    total: int


class ExamAssignmentBulkResponse(BaseModel):
    message: str
    assigned_count: int
    assignments: List[ExamAssignmentResponse]
