from pydantic import BaseModel, Field
from enum import Enum
from typing import Optional, List

class Judge0StatusEnum(str, Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    ACCEPTED = "accepted"
    WRONG_ANSWER = "wrong_answer"
    TIME_LIMIT_EXCEEDED = "time_limit_exceeded"
    MEMORY_LIMIT_EXCEEDED = "memory_limit_exceeded"
    RUNTIME_ERROR = "runtime_error"
    COMPILE_ERROR = "compile_error"
    INTERNAL_ERROR = "internal_error"
    UNKNOWN = "unknown"

class Judge0SubmissionRequest(BaseModel):
    source_code: str = Field(..., description="The source code to execute.")
    language_id: int = Field(..., description="Judge0 language ID.")
    stdin: Optional[str] = Field(None, description="Standard input for the program.")
    cpu_time_limit: Optional[int] = Field(None, description="Time limit in seconds.")
    memory_limit: Optional[int] = Field(None, description="Memory limit in MB.")
    # Additional optional fields can be added as needed.

class Judge0SubmissionResponse(BaseModel):
    token: str = Field(..., description="Token to poll for execution result.")

class Judge0ExecutionResult(BaseModel):
    status: Judge0StatusEnum = Field(..., description="Execution status.")
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    compile_output: Optional[str] = None
    time: Optional[float] = None  # seconds
    memory: Optional[int] = None  # KB
    message: Optional[str] = None
    token: Optional[str] = None
