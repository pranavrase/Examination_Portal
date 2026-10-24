from datetime import datetime, timezone
from sqlalchemy import Column, Integer, BigInteger, String, Text, Boolean, DateTime, ForeignKey, Index, CheckConstraint
from sqlalchemy.orm import relationship
from app.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


ALLOWED_NOTIFICATION_TYPES = {
    "EXAM_PUBLISHED",
    "EXAM_UPCOMING",
    "EXAM_AUTO_SUBMITTED",
    "RESULT_AVAILABLE",
    "RANKING_AVAILABLE",
    "SECURITY_ALERT",
    "ACCOUNT_UPDATE",
    "SYSTEM",
    "OTHER",
}


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, index=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(150), nullable=False)
    message = Column(Text, nullable=False)
    notification_type = Column(String(50), nullable=False, index=True)
    is_read = Column(Boolean, default=False, nullable=False, index=True)
    read_at = Column(DateTime, nullable=True)
    entity_type = Column(String(50), nullable=True)
    entity_id = Column(String(100), nullable=True)
    event_key = Column(String(120), nullable=True, unique=True, index=True)
    created_at = Column(DateTime, default=utc_now, nullable=False, index=True)

    user = relationship("User", foreign_keys=[user_id])

    __table_args__ = (
        Index("idx_notifications_user_unread_created", "user_id", "is_read", "created_at"),
        Index("idx_notifications_user_created", "user_id", "created_at"),
        CheckConstraint(
            "notification_type IN ('EXAM_PUBLISHED', 'EXAM_UPCOMING', 'EXAM_AUTO_SUBMITTED', "
            "'RESULT_AVAILABLE', 'RANKING_AVAILABLE', 'SECURITY_ALERT', 'ACCOUNT_UPDATE', 'SYSTEM', 'OTHER')",
            name="chk_notifications_type",
        ),
    )
