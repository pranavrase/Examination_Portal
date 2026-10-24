import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.db.base import Base
from app.db.session import engine, SessionLocal
from app.routers import auth, users, roles, exams, exam_assignments, questions, question_categories, mcq_engine, coding, students, examiner, autosave, exam_attempts, results, rankings, reports, activity_logs, security_monitoring, notifications, admin
from app.services.exam_attempt_service import auto_submit_expired_attempts

# Import all models so Base.metadata registers all tables from the PDF schema
from app.models import user as user_model
from app.models import activity as activity_model
from app.models import role as role_model
from app.models import exam as exam_model
from app.models import question as question_model
from app.models import attempt as attempt_model
from app.models import result as result_model
from app.models import log as log_model
from app.models import security as security_model
from app.models import notification as notification_model
from app.models import password_reset_otp as password_reset_otp_model

from app.services.role_service import seed_default_roles, seed_admin_account

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
    ]
)
logger = logging.getLogger(__name__)

# Create database tables
Base.metadata.create_all(bind=engine)

# Seed standard system default roles and default admin account
with SessionLocal() as db_session:
    seed_default_roles(db_session)
    seed_admin_account(db_session)

# Background task loop for auto-submitting expired attempts
async def _expiry_scheduler_worker():
    while True:
        try:
            await asyncio.sleep(30)
            with SessionLocal() as db_session:
                auto_submit_expired_attempts(db_session)
        except asyncio.CancelledError:
            break
        except Exception:
            pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start background expiry scheduler task
    scheduler_task = asyncio.create_task(_expiry_scheduler_worker())
    try:
        yield
    finally:
        scheduler_task.cancel()
        try:
            await scheduler_task
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Exam Portal API - User & Role Management Service (RBAC & PostgreSQL)",
    version="1.0.0",
    lifespan=lifespan,
)


@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    if isinstance(exc.detail, dict):
        message = exc.detail.get("message") or exc.detail.get("detail") or "Conflict"
        content = {
            "detail": message,
            "message": message,
            **exc.detail,
        }
        content["detail"] = message
        return JSONResponse(status_code=exc.status_code, content=content, headers=exc.headers)
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail}, headers=exc.headers)

# CORS Middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
        "http://localhost:3002",
        "http://127.0.0.1:3002",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:[0-9]+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(roles.router)
app.include_router(exams.router)
app.include_router(exam_assignments.router)
app.include_router(questions.router)
app.include_router(question_categories.router)
app.include_router(mcq_engine.router)
app.include_router(coding.router)
app.include_router(students.router)
app.include_router(examiner.router)
app.include_router(autosave.router)
app.include_router(exam_attempts.router)
app.include_router(results.router)
app.include_router(rankings.router)
app.include_router(reports.router)
app.include_router(activity_logs.router)
app.include_router(security_monitoring.router)
app.include_router(notifications.router)
app.include_router(admin.router)


@app.get("/", tags=["Health"])
def root():
    return {
        "status": "online",
        "service": settings.PROJECT_NAME,
        "database": settings.DATABASE_URL.split("@")[-1] if "@" in settings.DATABASE_URL else settings.DATABASE_URL,
        "message": "Welcome to Exam Portal API"
    }
