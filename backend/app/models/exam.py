from datetime import datetime, timezone
# pyrefly: ignore [missing-import]
from sqlalchemy import Column, Integer, BigInteger, String, Text, Numeric, Boolean, DateTime, ForeignKey, CheckConstraint, Index, UniqueConstraint
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import relationship
from app.db.base import Base


def utc_now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Exam(Base):
    __tablename__ = "exams"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, index=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    created_by = Column(BigInteger, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    status = Column(String(20), default="draft", nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    __table_args__ = (
        CheckConstraint("status IN ('draft', 'published', 'closed')", name="chk_exams_status"),
    )

    settings = relationship("ExamSettings", back_populates="exam", uselist=False, cascade="all, delete-orphan")
    assignments = relationship("ExamAssignment", back_populates="exam", cascade="all, delete-orphan")


class ExamSettings(Base):
    __tablename__ = "exam_settings"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, index=True, autoincrement=True)
    exam_id = Column(BigInteger, ForeignKey("exams.id", ondelete="CASCADE"), nullable=False, unique=True)
    duration_minutes = Column(Integer, nullable=False)
    total_marks = Column(Numeric(10, 2), nullable=False)
    passing_percentage = Column(Numeric(5, 2), nullable=False)
    negative_marking_ratio = Column(Numeric(5, 2), default=0, nullable=False)
    randomize_questions = Column(Boolean, default=False, nullable=False)
    randomize_options = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    __table_args__ = (
        CheckConstraint("passing_percentage BETWEEN 0 AND 100", name="chk_exam_settings_passing_percentage"),
        CheckConstraint("duration_minutes > 0", name="chk_exam_settings_duration_positive"),
    )

    exam = relationship("Exam", back_populates="settings")


class ExamAssignment(Base):
    __tablename__ = "exam_assignments"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, index=True, autoincrement=True)
    exam_id = Column(BigInteger, ForeignKey("exams.id", ondelete="CASCADE"), nullable=False)
    student_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    assigned_at = Column(DateTime, default=utc_now, nullable=False)
    scheduled_start = Column(DateTime, nullable=True)
    scheduled_end = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    __table_args__ = (
        UniqueConstraint("exam_id", "student_id", name="uq_exam_assignments_exam_student"),
        Index("idx_exam_assignments_exam_student", "exam_id", "student_id"),
    )

    exam = relationship("Exam", back_populates="assignments")
    student = relationship("User", foreign_keys=[student_id])


# Alias for singular/plural compatibility
ExamSetting = ExamSettings
