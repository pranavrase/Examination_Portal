from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class RankingItemResponse(BaseModel):
    rank: int = Field(description="Deterministic 1-based rank position")
    student_id: int = Field(description="Candidate student user ID")
    student_name: Optional[str] = Field(None, description="Full name of the student")
    student_email: Optional[str] = Field(None, description="Email address of the student")
    score: float = Field(description="Final score obtained in the exam")
    percentage: Optional[float] = Field(None, description="Percentage score")
    tie_break_time: Optional[str] = Field(None, description="Formatted completion duration or tie-breaker interval")
    submitted_at: Optional[datetime] = Field(None, description="Official submission timestamp")

    model_config = ConfigDict(from_attributes=True)


class LeaderboardResponse(BaseModel):
    exam_id: int = Field(description="Exam ID")
    exam_title: Optional[str] = Field(None, description="Title of the examination")
    total_candidates: int = Field(description="Total number of ranked candidates")
    rankings: List[RankingItemResponse] = Field(default_factory=list, description="Ranked candidate leaderboard")

    model_config = ConfigDict(from_attributes=True)


class MyRankResponse(BaseModel):
    exam_id: int = Field(description="Exam ID")
    exam_title: Optional[str] = Field(None, description="Title of the examination")
    student_id: int = Field(description="Candidate student user ID")
    student_name: Optional[str] = Field(None, description="Full name of the student")
    rank: int = Field(description="Student's assigned rank")
    score: float = Field(description="Final score obtained in the exam")
    percentage: Optional[float] = Field(None, description="Percentage score")
    total_candidates: int = Field(description="Total candidates participating in this exam")
    percentile: Optional[float] = Field(None, description="Student's percentile ranking across cohorts")
    tie_break_time: Optional[str] = Field(None, description="Formatted completion duration")
    submitted_at: Optional[datetime] = Field(None, description="Submission timestamp")

    model_config = ConfigDict(from_attributes=True)


class RankingComputeResponse(BaseModel):
    success: bool
    exam_id: int
    total_ranked: int
    message: str

    model_config = ConfigDict(from_attributes=True)
