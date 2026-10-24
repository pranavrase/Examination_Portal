from datetime import datetime, timezone
# pyrefly: ignore [missing-import]
from sqlalchemy import Column, Integer, BigInteger, String, Text, DateTime, JSON, ForeignKey, CheckConstraint, Index
from sqlalchemy.orm import relationship
from sqlalchemy.ext.hybrid import hybrid_property
from app.db.base import Base


def utc_now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, index=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    action_type = Column(String(50), nullable=False, index=True)
    entity_type = Column(String(50), nullable=True, index=True)
    entity_id = Column(String(100), nullable=True, index=True)
    description = Column(Text, nullable=True)
    metadata_json = Column("metadata", JSON, nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    occurred_at = Column(DateTime, default=utc_now, nullable=False, index=True)
    created_at = Column(DateTime, default=utc_now, nullable=False, index=True)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    user = relationship("User", foreign_keys=[user_id], backref="activity_logs")

    @hybrid_property
    def action(self) -> str:
        return self.action_type

    @action.setter
    def action(self, value: str):
        self.action_type = value

    @hybrid_property
    def details(self):
        return self.metadata_json

    @details.setter
    def details(self, value):
        self.metadata_json = value

    __table_args__ = (
        Index("idx_activity_logs_entity", "entity_type", "entity_id"),
        Index("idx_activity_logs_user_action", "user_id", "action_type"),
        CheckConstraint(
            "action_type IN ("
            "'login', 'logout', 'login_success', 'login_failed', "
            "'exam_start', 'exam_started', 'exam_submit', 'exam_submitted', 'exam_auto_submitted', "
            "'question_view', 'answer_save', 'code_draft_saved', 'password_change', 'profile_update', "
            "'exam_create', 'exam_created', 'exam_updated', 'exam_publish', 'exam_published', 'exam_archived', "
            "'question_created', 'question_updated', 'question_deleted', "
            "'result_calculated', 'ranking_generated', 'unauthorized_access', 'permission_denied', "
            "'user_created', 'user_updated', 'user_role_changed', 'user_disabled', 'system'"
            ")",
            name="chk_activity_logs_action_type"
        ),
    )


class TabSwitchLog(Base):
    __tablename__ = "tab_switch_logs"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, index=True, autoincrement=True)
    attempt_id = Column(BigInteger, ForeignKey("exam_attempts.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type = Column(String(20), nullable=False)
    occurred_at = Column(DateTime, default=utc_now, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "event_type IN ('tab_switch', 'page_refresh', 'window_blur')",
            name="chk_tab_switch_logs_event_type"
        ),
    )
