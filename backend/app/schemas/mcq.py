from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict


# ---------------------------------------------------------------------------
# Student-facing MCQ Question & Option Schemas (Zero-Knowledge / Anti-Leak)
# ---------------------------------------------------------------------------

class MCQOptionStudentResponse(BaseModel):
    id: int
    option_text: str

    model_config = ConfigDict(from_attributes=True)


class MCQQuestionStudentResponse(BaseModel):
    question_id: int
    question_text: str
    marks: float
    options: List[MCQOptionStudentResponse]
    selected_option_id: Optional[int] = None


class MCQExamQuestionsResponse(BaseModel):
    exam_id: int
    attempt_id: int
    status: str
    duration_minutes: int
    total_mcq_questions: int
    questions: List[MCQQuestionStudentResponse]


# ---------------------------------------------------------------------------
# Answer Recording & Updating Schemas
# ---------------------------------------------------------------------------

class MCQAnswerCreate(BaseModel):
    question_id: int = Field(..., gt=0, description="ID of the question being answered")
    selected_option_id: int = Field(..., gt=0, description="ID of the selected option")


class MCQAnswerUpdate(BaseModel):
    selected_option_id: int = Field(..., gt=0, description="Updated selected option ID")


class MCQAnswerResponse(BaseModel):
    attempt_id: int
    question_id: int
    selected_option_id: int
    answered_at: datetime
    message: str = "Answer recorded successfully"

    model_config = ConfigDict(from_attributes=True)


class MCQAttemptAnswerItem(BaseModel):
    question_id: int
    selected_option_id: Optional[int] = None
    answered_at: Optional[datetime] = None


class MCQAttemptAnswersResponse(BaseModel):
    attempt_id: int
    status: str
    answers: List[MCQAttemptAnswerItem]


# ---------------------------------------------------------------------------
# MCQ Scoring Schemas
# ---------------------------------------------------------------------------

class MCQQuestionScoreDetail(BaseModel):
    question_id: int
    marks_possible: float
    selected_option_id: Optional[int] = None
    is_correct: Optional[bool] = None
    marks_awarded: float


class MCQScoreResponse(BaseModel):
    attempt_id: int
    exam_id: int
    total_mcq_questions: int
    answered_questions: int
    unanswered_questions: int
    correct_answers: int
    incorrect_answers: int
    total_marks_possible: float
    total_marks_obtained: float
    breakdown: List[MCQQuestionScoreDetail] = []
