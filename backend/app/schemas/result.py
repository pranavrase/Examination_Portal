from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


# ---------------------------------------------------------------------------
# MCQ question breakdown (single question, never exposes correct option ID)
# ---------------------------------------------------------------------------
class MCQBreakdownItem(BaseModel):
    question_id: int
    effective_marks: float
    marks_awarded: float
    is_correct: Optional[bool] = None       # None means unanswered
    answered: bool = False

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Coding question breakdown (single question)
# ---------------------------------------------------------------------------
class CodingBreakdownItem(BaseModel):
    question_id: int
    coding_question_id: Optional[int] = None
    effective_marks: float
    marks_awarded: float
    submission_status: Optional[str] = None  # queued / accepted / etc.

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Score breakdown summary
# ---------------------------------------------------------------------------
class ScoreBreakdown(BaseModel):
    mcq_marks_obtained: float = Field(description="Total marks earned from MCQ questions")
    mcq_marks_possible: float = Field(description="Total marks possible from MCQ questions")
    coding_marks_obtained: float = Field(description="Total marks earned from coding questions")
    coding_marks_possible: float = Field(description="Total marks possible from coding questions")
    negative_marks_applied: float = Field(
        description="Total penalty applied (positive number representing deduction)"
    )
    mcq_breakdown: list[MCQBreakdownItem] = []
    coding_breakdown: list[CodingBreakdownItem] = []

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Primary result response (returned from GET /results/{attempt_id})
# ---------------------------------------------------------------------------
class ResultResponse(BaseModel):
    attempt_id: int
    exam_id: int
    student_id: int
    total_marks_obtained: float
    total_marks_possible: float
    percentage: float
    pass_fail: bool
    calculated_at: datetime
    breakdown: Optional[ScoreBreakdown] = None

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Lightweight result response (returned inline from submit endpoint)
# ---------------------------------------------------------------------------
class ResultSummaryResponse(BaseModel):
    attempt_id: int
    total_marks_obtained: float
    total_marks_possible: float
    percentage: float
    pass_fail: bool
    calculated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Examiner / Admin list view
# ---------------------------------------------------------------------------
class ResultListItem(BaseModel):
    attempt_id: int
    exam_id: int
    student_id: int
    student_email: Optional[str] = None
    student_name: Optional[str] = None
    total_marks_obtained: float
    total_marks_possible: float
    percentage: float
    pass_fail: bool
    calculated_at: datetime

    model_config = ConfigDict(from_attributes=True)
