from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    PROJECT_NAME: str = "Exam Portal API"
    API_V1_STR: str = "/auth"

    JWT_SECRET_KEY: str = "super-secret-key-change-this-in-production-1234567890"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    RESET_TOKEN_EXPIRE_MINUTES: int = 15

    DATABASE_URL: str = "postgresql://postgres:sanket@localhost:5432/exam_portal_db"

    JUDGE0_BASE_URL: str = "https://ce.judge0.com"
    JUDGE0_API_KEY: Optional[str] = None
    JUDGE0_RAPIDAPI_HOST: Optional[str] = None
    JUDGE0_TIMEOUT_SECONDS: int = 30
    JUDGE0_POLL_INTERVAL_SECONDS: float = 1.0
    JUDGE0_MAX_POLL_ATTEMPTS: int = 25
    EXECUTION_PROVIDER: str = "judge0"

    # Email/SMTP Configuration
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM_EMAIL: Optional[str] = None
    SMTP_FROM_NAME: str = "Examination Portal"
    SMTP_USE_TLS: bool = True

    # OTP Configuration
    OTP_EXPIRE_MINUTES: int = 10
    OTP_MAX_ATTEMPTS: int = 3
    OTP_RESEND_COOLDOWN_SECONDS: int = 60

    # Default Admin Configuration
    ADMIN_PASSWORD: str = "Pass@123"

    model_config = SettingsConfigDict(
        env_file=(".env", "backend/.env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
