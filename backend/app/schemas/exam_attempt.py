from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class StartAttemptRequest(BaseModel):
    """Optional payload when starting an attempt."""
    exam_id: Optional[int] = Field(None, description="Optional exam ID if supplied in request body")


class StartAttemptResponse(BaseModel):
    success: bool = True
    attempt_id: int
    exam_id: int
    status: str
    started_at: datetime
    duration_minutes: int
    remaining_seconds: int
    message: str = "Exam attempt started successfully"


class RemainingTimeResponse(BaseModel):
    attempt_id: int
    exam_id: int
    remaining_seconds: int
    status: str
    duration_minutes: int
    started_at: Optional[datetime] = None


class SubmitAttemptRequest(BaseModel):
    """Optional payload when student submits an attempt."""
    comments: Optional[str] = Field(None, max_length=500, description="Optional student feedback or notes")
    remaining_seconds_snapshot: Optional[int] = Field(None, description="Client-side snapshot for telemetry only")


class SubmitAttemptResponse(BaseModel):
    success: bool = True
    attempt_id: int
    status: str
    submitted_at: datetime
    message: str = "Exam submitted successfully"
    score: Optional[float] = None
    total_marks: Optional[float] = None
    percentage: Optional[float] = None
    pass_fail: Optional[bool] = None


class AutoSubmitResponse(BaseModel):
    success: bool = True
    expired_attempts_submitted: int
    message: str = "Auto-submit job executed successfully"
