from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class ExamPerformanceReport(BaseModel):
    exam_id: int = Field(description="Exam ID")
    exam_name: str = Field(description="Title / Name of the exam")
    exam_title: Optional[str] = Field(None, description="Title / Name of the exam (alias)")
    total_attempts: int = Field(0, description="Total attempts initiated")
    total_students: int = Field(0, description="Total distinct students attempted")
    completed_attempts: int = Field(0, description="Total submitted/completed attempts")
    in_progress_attempts: int = Field(0, description="Attempts currently in progress")
    passed_students: int = Field(0, description="Count of passed students")
    passed_count: int = Field(0, description="Count of passed students (alias)")
    failed_students: int = Field(0, description="Count of failed students")
    failed_count: int = Field(0, description="Count of failed students (alias)")
    average_score: float = Field(0.0, description="Average marks obtained by candidates")
    highest_score: float = Field(0.0, description="Highest marks obtained in the exam")
    lowest_score: float = Field(0.0, description="Lowest marks obtained in the exam")
    average_percentage: float = Field(0.0, description="Average percentage scored")

    model_config = ConfigDict(from_attributes=True)


class StudentPerformanceItem(BaseModel):
    exam_id: int = Field(description="Exam ID")
    exam_name: str = Field(description="Name/Title of the exam")
    attempt_id: int = Field(description="Attempt ID")
    status: str = Field(description="Attempt status (submitted/auto_submitted/in_progress)")
    total_marks: float = Field(description="Total marks possible")
    marks_obtained: float = Field(description="Marks obtained by student")
    percentage: float = Field(description="Percentage score")
    pass_fail: bool = Field(description="True if passed, False otherwise")
    rank: Optional[int] = Field(None, description="Rank in leaderboard if computed")
    submitted_at: Optional[datetime] = Field(None, description="Timestamp of submission")

    model_config = ConfigDict(from_attributes=True)


class StudentPerformanceReport(BaseModel):
    student_id: int = Field(description="Student user ID")
    student_name: str = Field(description="Full name of student")
    student_email: str = Field(description="Email address of student")
    total_exams_taken: int = Field(0, description="Total exams with completed attempts")
    passed_exams: int = Field(0, description="Total exams passed")
    failed_exams: int = Field(0, description="Total exams failed")
    average_percentage: float = Field(0.0, description="Average percentage across all taken exams")
    exams: List[StudentPerformanceItem] = Field(default_factory=list, description="Performance per exam")

    model_config = ConfigDict(from_attributes=True)


class QuestionPerformanceItem(BaseModel):
    question_id: int = Field(description="Question ID")
    question_text: str = Field(description="Question statement")
    question_type: str = Field(description="Type: mcq or coding")
    topic: Optional[str] = Field(None, description="Category / topic name")
    total_attempts: int = Field(0, description="Number of times answered/attempted")
    correct_count: int = Field(0, description="Count of correct answers")
    incorrect_count: int = Field(0, description="Count of incorrect answers")
    unanswered_count: int = Field(0, description="Count of candidates who left it unanswered")
    accuracy_percentage: float = Field(0.0, description="Accuracy percentage (correct / attempts * 100)")

    model_config = ConfigDict(from_attributes=True)


class ExamQuestionsReport(BaseModel):
    exam_id: int = Field(description="Exam ID")
    exam_title: str = Field(description="Exam Title")
    total_questions: int = Field(0, description="Total questions assigned to exam")
    questions: List[QuestionPerformanceItem] = Field(default_factory=list, description="Question performance stats")

    model_config = ConfigDict(from_attributes=True)


class CandidateWiseReportItem(BaseModel):
    rank: Optional[int] = Field(None, description="Candidate rank")
    candidate_id: int = Field(description="Student ID")
    student_id: int = Field(description="Student ID (alias)")
    candidate_name: str = Field(description="Student full name")
    student_name: str = Field(description="Student full name (alias)")
    candidate_email: Optional[str] = Field(None, description="Student email")
    exam_id: int = Field(description="Exam ID")
    exam_name: str = Field(description="Exam title")
    score: float = Field(description="Marks obtained")
    marks_obtained: float = Field(description="Marks obtained (alias)")
    total_marks: float = Field(description="Total marks possible")
    percentage: float = Field(description="Percentage score")
    status: str = Field(description="Status string: 'passed' or 'failed'")
    pass_fail_status: str = Field(description="Status string: 'passed' or 'failed'")
    attempt_date: Optional[datetime] = Field(None, description="Submission timestamp")

    model_config = ConfigDict(from_attributes=True)


class CandidateWiseReportResponse(BaseModel):
    total: int = Field(0, description="Total matching candidates")
    page: int = Field(1, description="Current page")
    limit: int = Field(15, description="Page size limit")
    candidates: List[CandidateWiseReportItem] = Field(default_factory=list, description="Candidate rows")

    model_config = ConfigDict(from_attributes=True)


class TopicWiseReportItem(BaseModel):
    topic: str = Field(description="Topic / Category name")
    candidates_attempted: int = Field(0, description="Number of candidates who answered questions in this topic")
    questions_count: int = Field(0, description="Number of questions under this topic in the exam(s)")
    avg_score: float = Field(0.0, description="Average marks scored in this topic")
    average_score: float = Field(0.0, description="Average marks scored in this topic (alias)")
    max_score: float = Field(0.0, description="Maximum marks scored in this topic")
    min_score: float = Field(0.0, description="Minimum marks scored in this topic")
    accuracy: float = Field(0.0, description="Accuracy percentage across all topic questions")
    correct_answers: int = Field(0, description="Total correct answers in topic")
    incorrect_answers: int = Field(0, description="Total incorrect answers in topic")
    unanswered_questions: int = Field(0, description="Total unanswered questions in topic")

    model_config = ConfigDict(from_attributes=True)


class TopicWiseReportResponse(BaseModel):
    topics: List[TopicWiseReportItem] = Field(default_factory=list, description="Topic aggregates")

    model_config = ConfigDict(from_attributes=True)
