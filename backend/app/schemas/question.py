from datetime import datetime
from typing import List, Optional, Any
from pydantic import BaseModel, Field, ConfigDict, model_validator


# ---------------------------------------------------------------------------
# Question Category Schemas
# ---------------------------------------------------------------------------

class QuestionCategoryBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=50, description="Category name (e.g. aptitude, reasoning, technical, coding)")
    topic: Optional[str] = Field(None, max_length=255, description="Specific topic within the category (e.g. Time & Work)")
    difficulty: Optional[str] = Field(None, max_length=20, description="Difficulty level: easy, medium, hard")

    @model_validator(mode="after")
    def validate_category_fields(self):
        if not self.name.strip():
            raise ValueError("Category name cannot be blank")
        if self.difficulty and self.difficulty.lower() not in {"easy", "medium", "hard"}:
            raise ValueError("Difficulty must be one of: easy, medium, hard")
        return self


class QuestionCategoryCreate(QuestionCategoryBase):
    pass


class QuestionCategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=50)
    topic: Optional[str] = Field(None, max_length=255)
    difficulty: Optional[str] = Field(None, max_length=20)

    @model_validator(mode="after")
    def validate_update_fields(self):
        if self.name is not None and not self.name.strip():
            raise ValueError("Category name cannot be blank")
        if self.difficulty is not None and self.difficulty.lower() not in {"easy", "medium", "hard"}:
            raise ValueError("Difficulty must be one of: easy, medium, hard")
        return self


class QuestionCategoryResponse(QuestionCategoryBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# MCQ Option Schemas
# ---------------------------------------------------------------------------

class MCQOptionBase(BaseModel):
    option_text: str = Field(..., min_length=1, description="Option text content")
    is_correct: bool = Field(default=False, description="Whether this option is the correct answer")

    @model_validator(mode="before")
    @classmethod
    def handle_text_alias(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "text" in data and "option_text" not in data:
                data["option_text"] = data["text"]
        return data

    @model_validator(mode="after")
    def validate_option_text(self):
        if not self.option_text.strip():
            raise ValueError("Option text cannot be blank")
        return self


class MCQOptionCreate(MCQOptionBase):
    pass


class MCQOptionUpdate(BaseModel):
    option_text: Optional[str] = Field(None, min_length=1)
    is_correct: Optional[bool] = None

    @model_validator(mode="after")
    def validate_update_option_text(self):
        if self.option_text is not None and not self.option_text.strip():
            raise ValueError("Option text cannot be blank")
        return self


class MCQOptionResponse(MCQOptionBase):
    id: int
    question_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Coding Test Case Schemas
# ---------------------------------------------------------------------------

class CodingTestCaseBase(BaseModel):
    input: Optional[str] = Field(default="", description="Input provided to the coding solution")
    expected_output: str = Field(..., description="Expected output from the coding solution")
    is_sample: bool = Field(default=False, description="Whether this test case is visible as a sample to candidates")
    is_hidden: bool = Field(default=False, description="Whether this test case is hidden for evaluation")

    @model_validator(mode="after")
    def validate_sample_xor_hidden(self):
        # Expected output must not be empty/pure whitespace
        if not self.expected_output.strip():
            raise ValueError("Expected output cannot be blank")

        if self.is_sample and self.is_hidden:
            raise ValueError("A test case cannot be both sample and hidden at the same time")
        if not self.is_sample and not self.is_hidden:
            # Default to hidden if not explicitly marked sample
            self.is_hidden = True
        return self


class CodingTestCaseCreate(CodingTestCaseBase):
    pass


class CodingTestCaseUpdate(BaseModel):
    input: Optional[str] = None
    expected_output: Optional[str] = None
    is_sample: Optional[bool] = None
    is_hidden: Optional[bool] = None

    @model_validator(mode="after")
    def validate_update_test_case(self):
        if self.expected_output is not None and not self.expected_output.strip():
            raise ValueError("Expected output cannot be blank")
        if self.is_sample is not None and self.is_hidden is not None:
            if self.is_sample and self.is_hidden:
                raise ValueError("A test case cannot be both sample and hidden at the same time")
            if not self.is_sample and not self.is_hidden:
                raise ValueError("A test case must be either sample or hidden")
        return self


class CodingTestCaseResponse(CodingTestCaseBase):
    id: int
    coding_question_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Coding Question Details Schemas
# ---------------------------------------------------------------------------

SUPPORTED_LANGUAGES = {"python", "java", "cpp", "c", "javascript", "go", "ruby", "rust", "csharp"}


class CodingQuestionBase(BaseModel):
    problem_statement: str = Field(..., min_length=1, description="Complete problem description")
    constraints: Optional[str] = Field(None, description="Problem constraints (e.g. 1 <= N <= 10^5)")
    allowed_languages: List[str] = Field(
        default=["python", "java", "cpp", "c"],
        description="List of allowed programming languages"
    )
    time_limit_ms: int = Field(default=2000, gt=0, description="Execution time limit in milliseconds (> 0)")
    memory_limit_kb: int = Field(default=256000, gt=0, description="Execution memory limit in kilobytes (> 0)")

    @model_validator(mode="after")
    def validate_coding_details(self):
        if not self.problem_statement.strip():
            raise ValueError("Problem statement cannot be blank")
        if not self.allowed_languages:
            raise ValueError("Allowed languages list cannot be empty")
        for lang in self.allowed_languages:
            if lang.lower() not in SUPPORTED_LANGUAGES:
                raise ValueError(f"Language '{lang}' is not supported. Supported: {', '.join(sorted(SUPPORTED_LANGUAGES))}")
        return self


class CodingQuestionCreate(CodingQuestionBase):
    test_cases: Optional[List[CodingTestCaseCreate]] = None


class CodingQuestionUpdate(BaseModel):
    problem_statement: Optional[str] = Field(None, min_length=1)
    constraints: Optional[str] = None
    allowed_languages: Optional[List[str]] = None
    time_limit_ms: Optional[int] = Field(None, gt=0)
    memory_limit_kb: Optional[int] = Field(None, gt=0)

    @model_validator(mode="after")
    def validate_update_coding(self):
        if self.problem_statement is not None and not self.problem_statement.strip():
            raise ValueError("Problem statement cannot be blank")
        if self.allowed_languages is not None:
            if not self.allowed_languages:
                raise ValueError("Allowed languages list cannot be empty")
            for lang in self.allowed_languages:
                if lang.lower() not in SUPPORTED_LANGUAGES:
                    raise ValueError(f"Language '{lang}' is not supported. Supported: {', '.join(sorted(SUPPORTED_LANGUAGES))}")
        return self


class CodingQuestionResponse(CodingQuestionBase):
    id: int
    question_id: int
    test_cases: List[CodingTestCaseResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Generic Question Schemas (MCQ & Coding Creation/Update)
# ---------------------------------------------------------------------------

class MCQQuestionCreate(BaseModel):
    category_id: int = Field(..., description="ID of existing QuestionCategory")
    question_type: str = Field(default="mcq", pattern="^mcq$")
    question_text: str = Field(..., min_length=1, description="Question title / prompt")
    marks: float = Field(..., gt=0, description="Marks allocated for correct answer (> 0)")
    options: List[MCQOptionCreate] = Field(..., description="List of MCQ options (at least 2 required)")

    @model_validator(mode="after")
    def validate_mcq_payload(self):
        if not self.question_text.strip():
            raise ValueError("Question text cannot be blank")
        if len(self.options) < 2:
            raise ValueError("MCQ questions must have at least 2 options")
        if not any(opt.is_correct for opt in self.options):
            raise ValueError("MCQ questions must have at least one correct option")
        return self


class CodingQuestionFullCreate(BaseModel):
    category_id: int = Field(..., description="ID of existing QuestionCategory")
    question_type: str = Field(default="coding", pattern="^coding$")
    question_text: str = Field(..., min_length=1, description="Question title")
    marks: float = Field(..., gt=0, description="Marks allocated for passing all test cases (> 0)")
    problem_statement: str = Field(..., min_length=1, description="Problem description")
    constraints: Optional[str] = None
    allowed_languages: List[str] = Field(default=["python", "java", "cpp", "c"])
    time_limit_ms: int = Field(default=2000, gt=0)
    memory_limit_kb: int = Field(default=256000, gt=0)
    test_cases: Optional[List[CodingTestCaseCreate]] = None

    @model_validator(mode="after")
    def validate_coding_full_payload(self):
        if not self.question_text.strip():
            raise ValueError("Question text cannot be blank")
        if not self.problem_statement.strip():
            raise ValueError("Problem statement cannot be blank")
        if not self.allowed_languages:
            raise ValueError("Allowed languages list cannot be empty")
        for lang in self.allowed_languages:
            if lang.lower() not in SUPPORTED_LANGUAGES:
                raise ValueError(f"Language '{lang}' is not supported. Supported: {', '.join(sorted(SUPPORTED_LANGUAGES))}")
        return self


class QuestionCreate(BaseModel):
    """Unified creation schema accepting either MCQ or Coding question payloads."""
    category_id: Optional[int] = Field(None, description="ID of existing QuestionCategory")
    category: Optional[str] = Field(None, description="Category name (used if category_id is not specified)")
    topic: Optional[str] = Field(None, description="Category topic")
    difficulty: Optional[str] = Field(None, description="Difficulty level")
    question_type: str = Field(..., pattern="^(mcq|coding)$", description="Type of question: mcq or coding")
    question_text: str = Field(..., min_length=1, description="Question title or text")
    marks: float = Field(..., gt=0, description="Marks (> 0)")
    # MCQ-specific fields
    options: Optional[List[MCQOptionCreate]] = None
    # Coding-specific fields
    problem_statement: Optional[str] = None
    constraints: Optional[str] = None
    allowed_languages: Optional[List[str]] = None
    time_limit_ms: Optional[int] = Field(None, gt=0)
    memory_limit_kb: Optional[int] = Field(None, gt=0)
    test_cases: Optional[List[CodingTestCaseCreate]] = None

    @model_validator(mode="after")
    def validate_unified_question(self):
        if not self.category_id and not self.category:
            raise ValueError("Either category_id or category name must be provided")

        if not self.question_text.strip():
            raise ValueError("Question text cannot be blank")

        if self.question_type == "mcq":
            if not self.options or len(self.options) < 2:
                raise ValueError("MCQ questions require at least 2 options")
            if not any(opt.is_correct for opt in self.options):
                raise ValueError("MCQ questions require at least one correct option")
            if self.problem_statement or self.test_cases:
                raise ValueError("Coding fields (problem_statement, test_cases) are not allowed on MCQ questions")

        elif self.question_type == "coding":
            if not self.problem_statement or not self.problem_statement.strip():
                raise ValueError("Coding questions require a non-empty problem_statement")
            if self.options and len(self.options) > 0:
                raise ValueError("MCQ options cannot be attached to a coding question")
            if self.allowed_languages:
                for lang in self.allowed_languages:
                    if lang.lower() not in SUPPORTED_LANGUAGES:
                        raise ValueError(f"Language '{lang}' is not supported. Supported: {', '.join(sorted(SUPPORTED_LANGUAGES))}")
            else:
                self.allowed_languages = ["python", "java", "cpp", "c"]
            if self.time_limit_ms is None:
                self.time_limit_ms = 2000
            if self.memory_limit_kb is None:
                self.memory_limit_kb = 256000

        return self


class QuestionUpdate(BaseModel):
    category_id: Optional[int] = None
    category: Optional[str] = None
    topic: Optional[str] = None
    difficulty: Optional[str] = None
    question_text: Optional[str] = Field(None, min_length=1)
    marks: Optional[float] = Field(None, gt=0)
    # MCQ options update
    options: Optional[List[MCQOptionCreate]] = None
    # Coding details update
    problem_statement: Optional[str] = None
    constraints: Optional[str] = None
    allowed_languages: Optional[List[str]] = None
    time_limit_ms: Optional[int] = Field(None, gt=0)
    memory_limit_kb: Optional[int] = Field(None, gt=0)

    @model_validator(mode="after")
    def validate_update(self):
        if self.question_text is not None and not self.question_text.strip():
            raise ValueError("Question text cannot be blank")
        if self.problem_statement is not None and not self.problem_statement.strip():
            raise ValueError("Problem statement cannot be blank")
        if self.options is not None:
            if len(self.options) < 2:
                raise ValueError("MCQ questions require at least 2 options")
            if not any(opt.is_correct for opt in self.options):
                raise ValueError("MCQ questions require at least one correct option")
        return self


class QuestionResponse(BaseModel):
    id: int
    category_id: int
    category: Optional[QuestionCategoryResponse] = None
    question_type: str
    question_text: str
    marks: float
    created_by: int
    mcq_options: List[MCQOptionResponse] = []
    coding_details: Optional[CodingQuestionResponse] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class QuestionDetailResponse(QuestionResponse):
    pass


class QuestionListResponse(BaseModel):
    items: List[QuestionResponse]
    page: int
    page_size: int
    total: int


# ---------------------------------------------------------------------------
# Bulk Import Schemas
# ---------------------------------------------------------------------------

class BulkImportRowError(BaseModel):
    row_index: int
    error: str


class BulkImportResponse(BaseModel):
    message: str
    total_rows: int
    successful_imports: int
    failed_imports: int
    errors: List[BulkImportRowError] = []
    imported_questions: List[QuestionResponse] = []
