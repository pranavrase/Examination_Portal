from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, model_validator


class MCQAutoSaveRequest(BaseModel):
    """
    Payload for auto-saving a student's MCQ answer during an active exam attempt.
    Also accepts batch payloads for seamless integration with frontend hook useAutoSave.
    """
    attempt_id: Optional[int] = Field(None, description="Optional attempt ID if provided in body")
    question_id: Optional[int] = Field(None, description="The Question ID being answered")
    selected_option_id: Optional[int] = Field(None, description="Selected MCQ option ID (or None if unselected)")

    # Support for frontend batch payload { mcq_answers: {...}, coding_drafts: {...} }
    mcq_answers: Optional[Dict[str, Optional[int]]] = Field(
        None,
        description="Optional dictionary mapping question_id -> selected_option_id for batch save"
    )
    coding_drafts: Optional[Dict[str, Any]] = Field(
        None,
        description="Optional dictionary mapping question_id -> { language, code/source_code } for batch save"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "question_id": 42,
                "selected_option_id": 105
            }
        }
    }


class CodeAutoSaveRequest(BaseModel):
    """
    Payload for auto-saving a student's in-progress coding draft without submitting or executing.
    """
    language: str = Field(..., min_length=1, max_length=50, description="Programming language (e.g. python, cpp, java, javascript)")
    source_code: str = Field(default="", max_length=100000, description="Current code snapshot")

    @model_validator(mode="before")
    @classmethod
    def check_code_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # If 'code' was passed instead of 'source_code', map it over
            if "source_code" not in data and "code" in data:
                data["source_code"] = data["code"]
        return data

    model_config = {
        "json_schema_extra": {
            "example": {
                "language": "python",
                "source_code": "def solution():\n    return 42"
            }
        }
    }


class MCQAutoSaveResponse(BaseModel):
    success: bool = True
    message: str = "Answer autosaved successfully"
    attempt_id: int
    question_id: Optional[int] = None
    selected_option_id: Optional[int] = None
    answered_at: Optional[datetime] = None


class CodeAutoSaveResponse(BaseModel):
    success: bool = True
    message: str = "Code draft autosaved successfully"
    attempt_id: int
    coding_question_id: int
    submission_id: Optional[int] = None
    language: str
    updated_at: Optional[datetime] = None


class BatchAutoSaveResponse(BaseModel):
    success: bool = True
    message: str = "Answers autosaved successfully"
    attempt_id: int
    saved_mcq_count: int
    saved_coding_draft_count: int
