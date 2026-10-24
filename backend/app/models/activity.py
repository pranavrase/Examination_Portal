from datetime import datetime, timezone
from sqlalchemy import Column, Integer, BigInteger, String, Boolean, DateTime, Text, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.ext.hybrid import hybrid_property
from app.db.base import Base
from app.models.log import ActivityLog


def utc_now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class LoginSession(Base):
    __tablename__ = "login_sessions"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, index=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    session_token_id = Column(String(255), nullable=False)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    login_at = Column(DateTime, default=utc_now, nullable=False)
    logout_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    user = relationship("User", back_populates="sessions")

    __table_args__ = (
        Index("idx_login_sessions_user_active", "user_id", "is_active"),
    )

    @hybrid_property
    def refresh_jti(self) -> str:
        return self.session_token_id

    @refresh_jti.setter
    def refresh_jti(self, value: str):
        self.session_token_id = value
