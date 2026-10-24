from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict


class CodingSubmissionCreate(BaseModel):
    language: str = Field(..., min_length=1, max_length=50, description="Programming language (e.g. 'python', 'java', 'cpp')")
    source_code: str = Field(..., min_length=1, description="Student source code")


class TestCaseResultResponse(BaseModel):
    test_case_id: int
    is_sample: bool
    status: str
    execution_time_ms: Optional[int] = None
    memory_used_kb: Optional[int] = None
    input: Optional[str] = None
    expected_output: Optional[str] = None
    actual_output: Optional[str] = None
    error_message: Optional[str] = None


class CodingSubmissionResponse(BaseModel):
    id: int
    attempt_id: int
    question_id: int
    language: str
    source_code: Optional[str] = None
    status: str
    score: float
    execution_time_ms: Optional[int] = None
    memory_used_kb: Optional[int] = None
    test_cases_total: int
    test_cases_passed: int
    test_cases: List[TestCaseResultResponse] = []
    submitted_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CodingSubmissionSummaryResponse(BaseModel):
    id: int
    attempt_id: int
    question_id: int
    language: str
    status: str
    score: float
    execution_time_ms: Optional[int] = None
    memory_used_kb: Optional[int] = None
    submitted_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CodingSubmissionListResponse(BaseModel):
    attempt_id: int
    total_submissions: int
    submissions: List[CodingSubmissionSummaryResponse]
