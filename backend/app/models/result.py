from datetime import datetime, timezone
from sqlalchemy import Column, Integer, BigInteger, String, Text, Numeric, Boolean, DateTime, Interval, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from app.db.base import Base


def utc_now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Result(Base):
    __tablename__ = "results"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, index=True, autoincrement=True)
    attempt_id = Column(BigInteger, ForeignKey("exam_attempts.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    total_marks_obtained = Column(Numeric(10, 2), nullable=False)
    total_marks_possible = Column(Numeric(10, 2), nullable=False)
    percentage = Column(Numeric(5, 2), nullable=False)
    pass_fail = Column(Boolean, nullable=False)
    calculated_at = Column(DateTime, default=utc_now, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    attempt = relationship("ExamAttempt", back_populates="result")


class Ranking(Base):
    __tablename__ = "rankings"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, index=True, autoincrement=True)
    exam_id = Column(BigInteger, ForeignKey("exams.id", ondelete="CASCADE"), nullable=False)
    student_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    rank = Column(Integer, nullable=False)
    score = Column(Numeric(10, 2), nullable=False)
    tie_break_time = Column(Interval, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    __table_args__ = (
        UniqueConstraint("exam_id", "student_id", name="uq_rankings_exam_student"),
        Index("idx_rankings_exam_rank", "exam_id", "rank"),
    )

    exam = relationship("Exam")
    student = relationship("User")
