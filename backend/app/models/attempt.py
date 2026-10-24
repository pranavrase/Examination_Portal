from datetime import datetime, timezone
# pyrefly: ignore [missing-import]
from sqlalchemy import Column, Integer, BigInteger, String, Text, Numeric, Boolean, DateTime, ForeignKey, CheckConstraint, Index, UniqueConstraint
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import relationship
from app.db.base import Base


def utc_now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class ExamAttempt(Base):
    __tablename__ = "exam_attempts"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, index=True, autoincrement=True)
    exam_id = Column(BigInteger, ForeignKey("exams.id", ondelete="CASCADE"), nullable=False)
    student_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    started_at = Column(DateTime, nullable=True)
    submitted_at = Column(DateTime, nullable=True)
    status = Column(String(20), default="in_progress", nullable=False)
    remaining_seconds_snapshot = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    __table_args__ = (
        CheckConstraint("status IN ('in_progress', 'submitted', 'auto_submitted')", name="chk_exam_attempts_status"),
        UniqueConstraint("exam_id", "student_id", name="uq_exam_attempts_exam_student"),
        Index("idx_exam_attempts_exam_student", "exam_id", "student_id"),
    )

    answers = relationship("AttemptAnswer", back_populates="attempt", cascade="all, delete-orphan")
    submissions = relationship("CodingSubmission", back_populates="attempt", cascade="all, delete-orphan")
    result = relationship("Result", back_populates="attempt", uselist=False, cascade="all, delete-orphan")
    exam = relationship("Exam")
    student = relationship("User")


class AttemptAnswer(Base):
    __tablename__ = "attempt_answers"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, index=True, autoincrement=True)
    attempt_id = Column(BigInteger, ForeignKey("exam_attempts.id", ondelete="CASCADE"), nullable=False, index=True)
    question_id = Column(BigInteger, ForeignKey("questions.id", ondelete="RESTRICT"), nullable=False, index=True)
    selected_option_id = Column(BigInteger, ForeignKey("mcq_options.id", ondelete="SET NULL"), nullable=True)
    is_correct = Column(Boolean, nullable=True)
    marks_awarded = Column(Numeric(10, 2), nullable=True)
    answered_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    __table_args__ = (
        UniqueConstraint("attempt_id", "question_id", name="uq_attempt_answers_attempt_question"),
    )

    attempt = relationship("ExamAttempt", back_populates="answers")
    question = relationship("Question")
    selected_option = relationship("McqOption")


class CodingSubmission(Base):
    __tablename__ = "coding_submissions"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, index=True, autoincrement=True)
    attempt_id = Column(BigInteger, ForeignKey("exam_attempts.id", ondelete="CASCADE"), nullable=False)
    coding_question_id = Column(BigInteger, ForeignKey("coding_questions.id", ondelete="RESTRICT"), nullable=False)
    language = Column(String(50), nullable=False)
    source_code = Column(Text, nullable=False)
    status = Column(String(30), default="queued", nullable=False)
    score = Column(Numeric(10, 2), default=0.0, nullable=False)
    execution_time_ms = Column(Integer, nullable=True)
    memory_used_kb = Column(Integer, nullable=True)
    submitted_at = Column(DateTime, default=utc_now, nullable=False, index=True)
    is_final = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    __table_args__ = (
        Index("idx_coding_submissions_attempt_coding_question", "attempt_id", "coding_question_id"),
    )

    attempt = relationship("ExamAttempt", back_populates="submissions")
    coding_question = relationship("CodingQuestion")
    execution_results = relationship("ExecutionResult", back_populates="submission", cascade="all, delete-orphan")


class ExecutionResult(Base):
    __tablename__ = "execution_results"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, index=True, autoincrement=True)
    submission_id = Column(BigInteger, ForeignKey("coding_submissions.id", ondelete="CASCADE"), nullable=False, index=True)
    test_case_id = Column(BigInteger, ForeignKey("coding_test_cases.id", ondelete="RESTRICT"), nullable=False)
    verdict = Column(String(20), nullable=False)
    actual_output = Column(Text, nullable=True)
    execution_time_ms = Column(Integer, nullable=True)
    memory_used_kb = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    __table_args__ = (
        CheckConstraint("verdict IN ('passed', 'failed', 'compile_error', 'runtime_error', 'tle')", name="chk_execution_results_verdict"),
    )

    submission = relationship("CodingSubmission", back_populates="execution_results")
