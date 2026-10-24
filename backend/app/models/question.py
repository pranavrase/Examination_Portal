from datetime import datetime, timezone
from sqlalchemy import Column, Integer, BigInteger, String, Text, Numeric, Boolean, DateTime, JSON, ForeignKey, CheckConstraint, Index, UniqueConstraint
from sqlalchemy.orm import relationship
from app.db.base import Base


def utc_now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class QuestionCategory(Base):
    __tablename__ = "question_categories"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, index=True, autoincrement=True)
    name = Column(String(50), nullable=False)
    topic = Column(String(255), nullable=True)
    difficulty = Column(String(20), nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    questions = relationship("Question", back_populates="category")


class Question(Base):
    __tablename__ = "questions"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, index=True, autoincrement=True)
    category_id = Column(BigInteger, ForeignKey("question_categories.id", ondelete="RESTRICT"), nullable=False, index=True)
    question_type = Column(String(20), nullable=False)
    question_text = Column(Text, nullable=False)
    marks = Column(Numeric(10, 2), nullable=False)
    created_by = Column(BigInteger, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    __table_args__ = (
        CheckConstraint("question_type IN ('mcq', 'coding')", name="chk_questions_question_type"),
    )

    category = relationship("QuestionCategory", back_populates="questions")
    creator = relationship("User", foreign_keys=[created_by])
    mcq_options = relationship("McqOption", back_populates="question", cascade="all, delete-orphan")
    coding_details = relationship("CodingQuestion", back_populates="question", uselist=False, cascade="all, delete-orphan")


class McqOption(Base):
    __tablename__ = "mcq_options"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, index=True, autoincrement=True)
    question_id = Column(BigInteger, ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True)
    option_text = Column(Text, nullable=False)
    is_correct = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    question = relationship("Question", back_populates="mcq_options")


class CodingQuestion(Base):
    __tablename__ = "coding_questions"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, index=True, autoincrement=True)
    question_id = Column(BigInteger, ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, unique=True)
    problem_statement = Column(Text, nullable=False)
    constraints = Column(Text, nullable=True)
    allowed_languages = Column(JSON, nullable=True)
    time_limit_ms = Column(Integer, nullable=True)
    memory_limit_kb = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    question = relationship("Question", back_populates="coding_details")
    test_cases = relationship("CodingTestCase", back_populates="coding_question", cascade="all, delete-orphan")


class CodingTestCase(Base):
    __tablename__ = "coding_test_cases"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, index=True, autoincrement=True)
    coding_question_id = Column(BigInteger, ForeignKey("coding_questions.id", ondelete="CASCADE"), nullable=False, index=True)
    input = Column(Text, nullable=True)
    expected_output = Column(Text, nullable=False)
    is_sample = Column(Boolean, default=False, nullable=False)
    is_hidden = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    __table_args__ = (
        CheckConstraint("is_sample <> is_hidden", name="chk_coding_test_cases_sample_xor_hidden"),
    )

    coding_question = relationship("CodingQuestion", back_populates="test_cases")


class ExamQuestion(Base):
    __tablename__ = "exam_questions"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, index=True, autoincrement=True)
    exam_id = Column(BigInteger, ForeignKey("exams.id", ondelete="CASCADE"), nullable=False)
    question_id = Column(BigInteger, ForeignKey("questions.id", ondelete="RESTRICT"), nullable=False)
    question_order = Column(Integer, nullable=False)
    marks_override = Column(Numeric(10, 2), nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    __table_args__ = (
        UniqueConstraint("exam_id", "question_id", name="uq_exam_questions_exam_question"),
        Index("idx_exam_questions_exam_question", "exam_id", "question_id"),
    )

    question = relationship("Question")


# Alias for naming consistency
MCQOption = McqOption
