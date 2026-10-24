from datetime import datetime, timezone, timedelta
from sqlalchemy import Column, Integer, BigInteger, String, Boolean, DateTime, Index
from app.db.base import Base


def utc_now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class PasswordResetOTP(Base):
    __tablename__ = "password_reset_otps"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, index=True, autoincrement=True)
    email = Column(String(255), nullable=False, index=True)
    otp_hash = Column(String(255), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    is_used = Column(Boolean, default=False, nullable=False)
    attempts = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    used_at = Column(DateTime, nullable=True)

    __table_args__ = (
        Index('idx_email_expires', 'email', 'expires_at'),
    )
