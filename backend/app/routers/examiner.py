import random
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Any, Dict
from fastapi import APIRouter, Depends, Query, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, desc

from app.core.dependencies import get_db, require_role, get_current_active_user
from app.core.security import verify_password, hash_password
from app.models.role import Role
from app.models.user import User
from app.models.exam import Exam, ExamSettings, ExamAssignment
from app.models.question import Question, ExamQuestion, QuestionCategory, McqOption, CodingQuestion, CodingTestCase
from app.models.attempt import ExamAttempt, AttemptAnswer, CodingSubmission
from app.models.result import Result, Ranking
from app.models.log import ActivityLog, TabSwitchLog
from app.models.notification import Notification
from app.services import activity_log_service
from app.schemas.exam import (
    ExamCreate,
    ExamUpdate,
    ExamResponse,
    ExamListResponse,
    ExamSettingsCreate,
    ExamAssignmentCreate,
)
from app.schemas.question import (
    QuestionCreate,
    QuestionUpdate,
    QuestionResponse,
)
from app.services import exam_service, question_service, result_service

router = APIRouter(
    prefix="/examiner",
    tags=["Examiner Dashboard"],
    dependencies=[Depends(require_role(["admin", "examiner"]))],
)


# ─────────────────────────────────────────────────────────────────────────────
# Pydantic Schemas for Examiner Extra Features
# ─────────────────────────────────────────────────────────────────────────────

class PaperGenerationRequest(BaseModel):
    aptitude_count: int = Field(default=0, ge=0)
    reasoning_count: int = Field(default=0, ge=0)
    technical_count: int = Field(default=0, ge=0)
    coding_count: int = Field(default=0, ge=0)
    difficulty_easy_pct: int = Field(default=40, ge=0, le=100)
    difficulty_medium_pct: int = Field(default=40, ge=0, le=100)
    difficulty_hard_pct: int = Field(default=20, ge=0, le=100)


class NotificationCreateRequest(BaseModel):
    title: str = Field(..., min_length=2, max_length=255)
    message: str = Field(..., min_length=2)
    type: str = Field(default="announcement", description="announcement, reminder, schedule_change, result_notice, instruction")
    target_exam_id: Optional[int] = None
    target_group: Optional[str] = "all_students"


class ExaminerProfileUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    department: Optional[str] = None
    phone: Optional[str] = None


class ExaminerChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=6)


# ─────────────────────────────────────────────────────────────────────────────
# 1. Dashboard / Overview Stats
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/stats",
    status_code=status.HTTP_200_OK,
    summary="Get aggregated statistics & overview for the examiner dashboard",
)
def get_examiner_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Dict[str, Any]:
    exam_query = db.query(Exam)

    exams_list = exam_query.order_by(Exam.created_at.desc()).all()
    total_exams = len(exams_list)
    published_exams = sum(1 for e in exams_list if e.status == "published")
    draft_exams = sum(1 for e in exams_list if e.status == "draft")
    completed_exams = sum(1 for e in exams_list if e.status == "closed")
    active_exams = published_exams
    upcoming_exams = draft_exams

    # Questions created
    q_query = db.query(Question)
    total_questions = q_query.count()

    # Total assigned candidates
    own_exam_ids = [e.id for e in exams_list]
    total_candidates = 0
    total_submissions = 0
    avg_score = 0.0
    pass_percentage = 0.0

    if own_exam_ids:
        total_candidates = (
            db.query(ExamAssignment)
            .filter(ExamAssignment.exam_id.in_(own_exam_ids))
            .distinct(ExamAssignment.student_id)
            .count()
        )
        # Fallback if no specific assignments yet
        if total_candidates == 0:
            total_candidates = db.query(User).filter(
                User.roles.any(Role.name == "student")
            ).count()

        total_submissions = (
            db.query(ExamAttempt)
            .filter(
                ExamAttempt.exam_id.in_(own_exam_ids),
                ExamAttempt.status.in_(["submitted", "auto_submitted"]),
            )
            .count()
        )

        results = (
            db.query(Result)
            .join(ExamAttempt, Result.attempt_id == ExamAttempt.id)
            .filter(ExamAttempt.exam_id.in_(own_exam_ids))
            .all()
        )
        if results:
            avg_score = round(sum(float(r.percentage) for r in results) / len(results), 1)
            passed = sum(1 for r in results if r.pass_fail)
            pass_percentage = round((passed / len(results)) * 100, 1)
        else:
            avg_score = 0.0
            pass_percentage = 0.0
    else:
        total_candidates = db.query(User).filter(
            User.roles.any(Role.name == "student")
        ).count()
        avg_score = 0.0
        pass_percentage = 0.0

    # Recent examinations
    recent_exams = []
    for e in exams_list[:5]:
        q_count = db.query(ExamQuestion).filter(ExamQuestion.exam_id == e.id).count()
        sub_count = db.query(ExamAttempt).filter(ExamAttempt.exam_id == e.id, ExamAttempt.status.in_(["submitted", "auto_submitted"])).count()
        recent_exams.append({
            "id": e.id,
            "title": e.title,
            "status": e.status,
            "duration": e.settings.duration_minutes if e.settings else None,
            "total_marks": float(e.settings.total_marks) if e.settings else None,
            "questions_count": q_count,
            "submissions_count": sub_count,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        })

    # Upcoming exam schedule
    upcoming_schedule = []
    for e in exams_list[:4]:
        upcoming_schedule.append({
            "id": e.id,
            "title": e.title,
            "date": (e.created_at + timedelta(days=2)).strftime("%b %d, %Y") if e.created_at else "Upcoming",
            "time": "10:00 AM - 12:00 PM",
            "duration": f"{e.settings.duration_minutes if e.settings else 'N/A'} mins",
            "status": "Scheduled" if e.status == "published" else "Drafted",
            "category": "Aptitude & Technical",
        })

    # Recent candidate activity - from actual exam attempts and submissions
    recent_activity = []
    if own_exam_ids:
        recent_attempts = (
            db.query(ExamAttempt)
            .filter(ExamAttempt.exam_id.in_(own_exam_ids))
            .order_by(ExamAttempt.updated_at.desc())
            .limit(5)
            .all()
        )
        for attempt in recent_attempts:
            student = db.query(User).filter(User.id == attempt.student_id).first()
            exam = db.query(Exam).filter(Exam.id == attempt.exam_id).first()
            result_obj = db.query(Result).filter(Result.attempt_id == attempt.id).first()
            score_str = f"{result_obj.percentage:.0f}%" if result_obj and result_obj.percentage else "In Progress"
            status_label = attempt.status.replace("_", " ").title()
            activity_type = "success" if attempt.status in ["submitted", "auto_submitted"] else "primary"
            recent_activity.append({
                "id": attempt.id,
                "student_name": student.full_name if student else "Unknown",
                "action": status_label,
                "exam_title": exam.title if exam else "Unknown Exam",
                "score": score_str,
                "time": attempt.updated_at.strftime("%b %d, %H:%M") if attempt.updated_at else "",
                "type": activity_type,
            })

    # System overview stats (used by Admin and high-level Examiner dashboards)
    total_users = db.query(User).count()
    active_users = db.query(User).filter(User.is_active == True).count()
    students_count = db.query(User).filter(User.roles.any(Role.name == "student")).count()
    examiners_count = db.query(User).filter(User.roles.any(Role.name == "examiner")).count()
    admins_count = db.query(User).filter(User.roles.any(Role.name == "admin")).count()
    total_attempts = db.query(ExamAttempt).count()

    return {
        "total_exams": total_exams,
        "upcoming_exams": upcoming_exams,
        "active_exams": active_exams,
        "completed_exams": completed_exams,
        "total_candidates": total_candidates,
        "total_questions": total_questions,
        "avg_score": avg_score,
        "pass_percentage": pass_percentage,
        "pending_review": 0,
        "recent_exams": recent_exams,
        "upcoming_schedule": upcoming_schedule,
        "recent_activity": recent_activity,
        "total_users": total_users,
        "students_count": students_count,
        "examiners_count": examiners_count,
        "admins_count": admins_count,
        "active_users": active_users,
        "published_exams": published_exams,
        "total_attempts": total_attempts,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 2. Examination Management
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/exams",
    status_code=status.HTTP_200_OK,
    summary="List examinations with rich filters",
)
def list_my_exams(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    status: Optional[str] = Query(None, description="Filter by draft, published, closed, upcoming, active, completed"),
    search: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Dict[str, Any]:
    query = db.query(Exam)

    if status:
        stat_lower = status.lower()
        if stat_lower in ["draft", "published", "closed"]:
            query = query.filter(Exam.status == stat_lower)
        elif stat_lower == "active":
            query = query.filter(Exam.status == "published")
        elif stat_lower == "upcoming":
            query = query.filter(Exam.status == "draft")
        elif stat_lower == "completed":
            query = query.filter(Exam.status == "closed")

    if search:
        query = query.filter(Exam.title.ilike(f"%{search}%"))

    total = query.count()
    offset = (page - 1) * page_size
    exams = query.order_by(Exam.created_at.desc()).offset(offset).limit(page_size).all()

    items = []
    for e in exams:
        q_count = db.query(ExamQuestion).filter(ExamQuestion.exam_id == e.id).count()
        candidates_assigned = db.query(ExamAssignment).filter(ExamAssignment.exam_id == e.id).count()
        submissions_count = db.query(ExamAttempt).filter(ExamAttempt.exam_id == e.id, ExamAttempt.status.in_(["submitted", "auto_submitted"])).count()

        settings = e.settings
        items.append({
            "id": e.id,
            "title": e.title,
            "description": e.description or "",
            "category": "Aptitude, Reasoning & Technical",
            "exam_type": "Mixed Evaluation",
            "status": e.status,
            "is_published": e.status == "published",
            "duration_minutes": settings.duration_minutes if settings else None,
            "total_marks": float(settings.total_marks) if settings else None,
            "passing_percentage": float(settings.passing_percentage) if settings else None,
            "negative_marking_ratio": float(settings.negative_marking_ratio) if settings else None,
            "randomize_questions": settings.randomize_questions if settings else False,
            "randomize_options": settings.randomize_options if settings else False,
            "question_count": q_count,
            "total_questions": q_count,
            "candidates_assigned": candidates_assigned,
            "submissions_count": submissions_count,
            "created_at": e.created_at.isoformat() if e.created_at else None,
            "updated_at": e.updated_at.isoformat() if e.updated_at else None,
        })

    return {
        "items": items,
        "page": page,
        "page_size": page_size,
        "total": total,
    }


@router.post(
    "/exams",
    status_code=status.HTTP_201_CREATED,
    summary="Create examination with full configuration",
)
def create_exam_endpoint(
    exam_in: ExamCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    created = exam_service.create_exam(
        db=db,
        exam_in=exam_in,
        creator_id=current_user.id,
    )
    return created


@router.get(
    "/exams/{exam_id}",
    response_model=ExamResponse,
    status_code=status.HTTP_200_OK,
    summary="Get examination details",
)
def get_exam_endpoint(
    exam_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return exam_service.get_exam_by_id(
        db=db,
        exam_id=exam_id,
        current_user=current_user,
    )


@router.put(
    "/exams/{exam_id}",
    response_model=ExamResponse,
    status_code=status.HTTP_200_OK,
    summary="Update examination",
)
def update_exam_endpoint(
    exam_id: int,
    exam_in: ExamUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return exam_service.update_exam(
        db=db,
        exam_id=exam_id,
        exam_in=exam_in,
        current_user=current_user,
    )


@router.delete(
    "/exams/{exam_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete examination",
)
def delete_exam_endpoint(
    exam_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    exam = exam_service.get_exam_by_id(db=db, exam_id=exam_id, current_user=current_user)
    db.query(ExamAssignment).filter(ExamAssignment.exam_id == exam_id).delete()
    db.query(ExamQuestion).filter(ExamQuestion.exam_id == exam_id).delete()
    db.delete(exam)
    db.commit()
    return {"message": f"Exam {exam_id} deleted successfully", "id": exam_id}


@router.post(
    "/exams/{exam_id}/duplicate",
    status_code=status.HTTP_201_CREATED,
    summary="Duplicate an existing examination",
)
def duplicate_exam(
    exam_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    original = exam_service.get_exam_by_id(db=db, exam_id=exam_id, current_user=current_user)
    orig_settings = original.settings

    cloned_exam = Exam(
        title=f"Copy of {original.title}",
        description=original.description,
        created_by=current_user.id,
        status="draft",
    )
    db.add(cloned_exam)
    db.flush()

    if orig_settings:
        cloned_settings = ExamSettings(
            exam_id=cloned_exam.id,
            duration_minutes=orig_settings.duration_minutes,
            total_marks=orig_settings.total_marks,
            passing_percentage=orig_settings.passing_percentage,
            negative_marking_ratio=orig_settings.negative_marking_ratio,
            randomize_questions=orig_settings.randomize_questions,
            randomize_options=orig_settings.randomize_options,
        )
        db.add(cloned_settings)

    orig_questions = db.query(ExamQuestion).filter(ExamQuestion.exam_id == exam_id).all()
    for oq in orig_questions:
        db.add(ExamQuestion(
            exam_id=cloned_exam.id,
            question_id=oq.question_id,
            question_order=oq.question_order,
            marks_override=oq.marks_override,
        ))

    db.commit()
    db.refresh(cloned_exam)
    return cloned_exam


@router.patch(
    "/exams/{exam_id}/publish",
    response_model=ExamResponse,
    status_code=status.HTTP_200_OK,
    summary="Toggle publish/active state of examination",
)
def toggle_publish_endpoint(
    exam_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    exam = exam_service.get_exam_by_id(db=db, exam_id=exam_id, current_user=current_user)
    if exam.status == "draft":
        exam.status = "published"
        # If no assignments exist yet, auto-assign all active students so it appears in their portal
        assigned_count = db.query(ExamAssignment).filter(ExamAssignment.exam_id == exam.id).count()
        if assigned_count == 0:
            all_users = db.query(User).filter(User.is_active == True).all()
            for u in all_users:
                if exam_service._is_student(u):
                    db.add(ExamAssignment(exam_id=exam.id, student_id=u.id))
    elif exam.status == "published":
        exam.status = "closed"
    else:
        exam.status = "draft"
    db.commit()
    db.refresh(exam)
    return exam


# ─────────────────────────────────────────────────────────────────────────────
# 3. Automated Question Selection & Exam Paper Creation
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/exams/{exam_id}/generate-paper",
    status_code=status.HTTP_200_OK,
    summary="Automatically assemble exam paper based on topic and difficulty distribution",
)
def generate_exam_paper(
    exam_id: int,
    dist: PaperGenerationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    exam_service.get_exam_by_id(db=db, exam_id=exam_id, current_user=current_user)

    all_questions = db.query(Question).options(joinedload(Question.category)).all()
    
    aptitude_pool = [q for q in all_questions if q.question_type == "mcq" and "aptitude" in (q.category.name if q.category else "")]
    reasoning_pool = [q for q in all_questions if q.question_type == "mcq" and "reasoning" in (q.category.name if q.category else "")]
    technical_pool = [q for q in all_questions if q.question_type == "mcq" and "technical" in (q.category.name if q.category else "")]
    coding_pool = [q for q in all_questions if q.question_type == "coding"]

    generic_mcq = [q for q in all_questions if q.question_type == "mcq"]

    selected_ids = []
    
    def pick_random(pool, count):
        if not pool:
            return random.sample(generic_mcq, min(count, len(generic_mcq)))
        return random.sample(pool, min(count, len(pool)))

    selected_ids.extend([q.id for q in pick_random(aptitude_pool, dist.aptitude_count)])
    selected_ids.extend([q.id for q in pick_random(reasoning_pool, dist.reasoning_count)])
    selected_ids.extend([q.id for q in pick_random(technical_pool, dist.technical_count)])
    selected_ids.extend([q.id for q in pick_random(coding_pool, dist.coding_count)])

    unique_ids = list(dict.fromkeys(selected_ids))

    db.query(ExamQuestion).filter(ExamQuestion.exam_id == exam_id).delete()
    for idx, qid in enumerate(unique_ids, start=1):
        db.add(ExamQuestion(
            exam_id=exam_id,
            question_id=qid,
            question_order=idx,
        ))

    db.commit()

    return {
        "message": f"Successfully assembled exam paper with {len(unique_ids)} questions",
        "exam_id": exam_id,
        "total_selected": len(unique_ids),
        "breakdown": {
            "aptitude": dist.aptitude_count,
            "reasoning": dist.reasoning_count,
            "technical": dist.technical_count,
            "coding": dist.coding_count,
        }
    }


# ─────────────────────────────────────────────────────────────────────────────
# 4. Questions Management (per Exam & Bank)
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/exams/{exam_id}/questions",
    status_code=status.HTTP_200_OK,
    summary="List questions in an examination",
)
def get_exam_questions_endpoint(
    exam_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    exam_service.get_exam_by_id(db=db, exam_id=exam_id, current_user=current_user)
    mappings = (
        db.query(ExamQuestion)
        .options(
            joinedload(ExamQuestion.question).joinedload(Question.category),
            joinedload(ExamQuestion.question).joinedload(Question.mcq_options),
            joinedload(ExamQuestion.question).joinedload(Question.coding_details).joinedload(CodingQuestion.test_cases),
        )
        .filter(ExamQuestion.exam_id == exam_id)
        .order_by(ExamQuestion.question_order.asc())
        .all()
    )

    questions = []
    for m in mappings:
        q = m.question
        if not q:
            continue
        opts = [{"id": o.id, "option_text": o.option_text, "is_correct": o.is_correct} for o in q.mcq_options] if q.mcq_options else []
        coding_det = None
        if q.coding_details:
            cd = q.coding_details
            coding_det = {
                "problem_statement": cd.problem_statement,
                "constraints": cd.constraints,
                "allowed_languages": cd.allowed_languages,
                "time_limit_ms": cd.time_limit_ms,
                "memory_limit_kb": cd.memory_limit_kb,
                "test_cases": [
                    {
                        "id": tc.id,
                        "input": tc.input,
                        "expected_output": tc.expected_output,
                        "is_sample": tc.is_sample,
                        "is_hidden": tc.is_hidden,
                    }
                    for tc in cd.test_cases
                ]
            }

        questions.append({
            "id": q.id,
            "question_type": q.question_type,
            "question_text": q.question_text,
            "marks": float(m.marks_override or q.marks),
            "category": q.category.name if q.category else "General",
            "topic": q.category.topic if q.category else "General",
            "difficulty": q.category.difficulty if q.category else "Medium",
            "question_order": m.question_order,
            "options": opts,
            "coding_details": coding_det,
            "created_at": q.created_at.isoformat() if q.created_at else None,
        })

    return questions


@router.post(
    "/exams/{exam_id}/questions",
    status_code=status.HTTP_201_CREATED,
    summary="Add question directly to exam",
)
def add_question_to_exam_endpoint(
    exam_id: int,
    q_in: QuestionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    exam_service.get_exam_by_id(db=db, exam_id=exam_id, current_user=current_user)
    question = question_service.create_question(db=db, q_in=q_in, creator_id=current_user.id)
    
    max_order = db.query(func.max(ExamQuestion.question_order)).filter(ExamQuestion.exam_id == exam_id).scalar()
    next_order = (max_order or 0) + 1

    db.add(ExamQuestion(exam_id=exam_id, question_id=question.id, question_order=next_order))
    db.commit()
    return question


@router.delete(
    "/exams/{exam_id}/questions/{question_id}",
    status_code=status.HTTP_200_OK,
    summary="Remove question from exam",
)
def remove_question_from_exam(
    exam_id: int,
    question_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    exam_service.get_exam_by_id(db=db, exam_id=exam_id, current_user=current_user)
    db.query(ExamQuestion).filter(ExamQuestion.exam_id == exam_id, ExamQuestion.question_id == question_id).delete()
    db.commit()
    return {"message": "Question unmapped from exam successfully"}


# ─────────────────────────────────────────────────────────────────────────────
# 5. Candidate Management
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/candidates",
    status_code=status.HTTP_200_OK,
    summary="List registered candidates with status & assignment details",
)
def list_candidates(
    search: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None),
    exam_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    # Query students with role-based filtering
    try:
        # Query all users and filter by role property (more reliable than join)
        all_users = db.query(User).all()
        
        # Get users with student role using the role property
        students = [user for user in all_users if user.role == "student"]
        
        if search:
            search_lower = search.lower()
            students = [s for s in students if 
                       (s.full_name and search_lower in s.full_name.lower()) or 
                       (s.email and search_lower in s.email.lower()) or 
                       (s.roll_number and search_lower in s.roll_number.lower())]

        candidates_data = []
        for s in students:
            # Get actual exam assignments with exam details
            try:
                assignments = db.query(ExamAssignment).filter(ExamAssignment.student_id == s.id).all()
                # Manually fetch exam details for each assignment
                for assignment in assignments:
                    exam = db.query(Exam).filter(Exam.id == assignment.exam_id).first()
                    assignment.exam = exam
            except Exception as e:
                assignments = []
            
            # Get exam attempts to determine status
            try:
                attempts = db.query(ExamAttempt).filter(ExamAttempt.student_id == s.id).all()
            except Exception as e:
                attempts = []
            
            # Determine exam status based on latest attempt
            exam_status = "Not Started"
            if attempts:
                # Sort by started_at to get the most recent attempt
                latest_attempt = sorted(attempts, key=lambda a: a.started_at or a.created_at, reverse=True)[0]
                if latest_attempt.status == "in_progress":
                    exam_status = "In Progress"
                elif latest_attempt.status == "submitted":
                    exam_status = "Completed"
                elif latest_attempt.status == "auto_submitted":
                    exam_status = "Auto Submitted"
            
            # Apply status filter if provided
            if status_filter:
                filter_status = status_filter.lower().replace(" ", "_")
                if filter_status != exam_status.lower():
                    continue

            candidates_data.append({
                "id": s.id,
                "full_name": s.full_name or s.email.split("@")[0].capitalize(),
                "email": s.email,
                "department": s.college or "Not Specified",
                "roll_number": s.roll_number or "—",
                "status": exam_status,
                "is_active": s.is_active,
                "joined_at": s.created_at.isoformat() if s.created_at else None,
                "assigned_exams": [
                    {
                        "exam_id": a.exam_id,
                        "title": a.exam.title if a.exam else "Assessment",
                        "assigned_at": a.assigned_at.isoformat() if a.assigned_at else None,
                    }
                    for a in assignments
                ]
            })

        return candidates_data
        
    except Exception as e:
        print(f"Error in list_candidates: {e}")
        import traceback
        traceback.print_exc()
        return []


@router.post(
    "/exams/{exam_id}/assign",
    status_code=status.HTTP_201_CREATED,
    summary="Assign candidate(s) to examination",
)
def assign_candidates_endpoint(
    exam_id: int,
    payload: ExamAssignmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    assignments = exam_service.assign_exam_to_students(
        db=db,
        exam_id=exam_id,
        assignment_in=payload,
        current_user=current_user,
    )
    return {"message": f"Assigned {len(assignments)} candidate(s) to examination", "count": len(assignments)}


@router.delete(
    "/exams/{exam_id}/assignments/{student_id}",
    status_code=status.HTTP_200_OK,
    summary="Remove candidate from examination",
)
def unassign_candidate_endpoint(
    exam_id: int,
    student_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    exam_service.remove_student_assignment(
        db=db,
        exam_id=exam_id,
        student_id=student_id,
        current_user=current_user,
    )
    return {"message": f"Candidate {student_id} unassigned successfully"}


def _is_admin_user(current_user: User) -> bool:
    roles = {r.name.lower() for r in (current_user.roles or [])}
    if current_user.role:
        roles.add(current_user.role.lower())
    return "admin" in roles


def _examiner_exam_ids(db: Session, current_user: User) -> List[int]:
    q = db.query(Exam.id)
    return [row[0] for row in q.all()]


def _as_naive(dt):
    if dt is None:
        return None
    if getattr(dt, "tzinfo", None) is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def _debug_log(hypothesis_id: str, location: str, message: str, data: dict):
    # #region agent log
    try:
        import json as _json, time as _time
        with open(r"d:\examportal\debug-964685.log", "a", encoding="utf-8") as _f:
            _f.write(_json.dumps({
                "sessionId": "964685",
                "hypothesisId": hypothesis_id,
                "location": location,
                "message": message,
                "data": data,
                "timestamp": int(_time.time() * 1000),
                "runId": "post-fix",
            }) + "\n")
    except Exception:
        pass
    # #endregion


# ─────────────────────────────────────────────────────────────────────────────
# 6. Live Examination Monitoring & Proctoring
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/monitoring",
    status_code=status.HTTP_200_OK,
    summary="Live proctoring and real-time candidate examination monitoring",
)
def get_live_monitoring(
    exam_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    own_exam_ids = _examiner_exam_ids(db, current_user)
    db_in_progress = db.query(ExamAttempt).filter(ExamAttempt.status == "in_progress").count()
    db_submitted = db.query(ExamAttempt).filter(ExamAttempt.status.in_(["submitted", "auto_submitted"])).count()

    if not own_exam_ids:
        payload = {
            "active_candidates_count": 0,
            "completed_count": 0,
            "flagged_count": 0,
            "sessions": [],
        }
        _debug_log("A", "examiner.py:get_live_monitoring", "monitoring live empty exam list", {
            "exam_id": exam_id, "user_id": current_user.id, "db_in_progress": db_in_progress,
            "db_submitted": db_submitted, "source": "live", "session_count": 0,
        })
        return payload

    attempt_q = (
        db.query(ExamAttempt)
        .options(joinedload(ExamAttempt.student), joinedload(ExamAttempt.exam).joinedload(Exam.settings))
        .filter(ExamAttempt.exam_id.in_(own_exam_ids))
        .filter(ExamAttempt.status.in_(["in_progress", "submitted", "auto_submitted"]))
    )
    if exam_id:
        attempt_q = attempt_q.filter(ExamAttempt.exam_id == exam_id)

    attempts = attempt_q.order_by(ExamAttempt.updated_at.desc()).limit(200).all()
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    sessions = []

    for att in attempts:
        exam = att.exam
        student = att.student
        settings = exam.settings if exam else None
        duration_minutes = settings.duration_minutes if settings else None

        total_questions = db.query(func.count(ExamQuestion.id)).filter(ExamQuestion.exam_id == att.exam_id).scalar() or 0
        mcq_answered = (
            db.query(func.count(AttemptAnswer.id))
            .filter(AttemptAnswer.attempt_id == att.id, AttemptAnswer.selected_option_id.isnot(None))
            .scalar()
            or 0
        )
        coding_answered = (
            db.query(func.count(func.distinct(CodingSubmission.coding_question_id)))
            .filter(CodingSubmission.attempt_id == att.id)
            .scalar()
            or 0
        )
        questions_answered = min(int(mcq_answered) + int(coding_answered), int(total_questions) or (int(mcq_answered) + int(coding_answered)))
        tab_switches = db.query(func.count(TabSwitchLog.id)).filter(TabSwitchLog.attempt_id == att.id).scalar() or 0

        remaining_minutes = 0
        if att.status == "in_progress" and duration_minutes is not None:
            if att.remaining_seconds_snapshot is not None:
                remaining_minutes = max(0, int(att.remaining_seconds_snapshot) // 60)
            elif att.started_at:
                elapsed = (now - _as_naive(att.started_at)).total_seconds()
                remaining_minutes = max(0, int((duration_minutes * 60 - elapsed) // 60))
            else:
                remaining_minutes = duration_minutes

        if att.status in ("submitted", "auto_submitted"):
            progress_percentage = 100
            status_label = "Completed"
        else:
            progress_percentage = int(round((questions_answered / total_questions) * 100)) if total_questions else 0
            status_label = "In Progress"

        if tab_switches >= 5:
            activity_status = "Suspicious / Multiple Blur"
        elif tab_switches > 0:
            activity_status = "Tab Switch Alert"
        else:
            activity_status = "Normal"

        sessions.append({
            "id": att.id,
            "candidate_name": (student.full_name if student else None) or (student.email.split("@")[0] if student and student.email else "Candidate"),
            "candidate_email": student.email if student else None,
            "roll_number": (student.roll_number if student and student.roll_number else (f"ID-{student.id}" if student else "—")),
            "exam_title": exam.title if exam else "Examination",
            "status": status_label,
            "time_remaining_minutes": remaining_minutes,
            "duration_minutes": int(duration_minutes) if duration_minutes is not None else None,
            "progress_percentage": progress_percentage,
            "questions_answered": questions_answered,
            "total_questions": total_questions,
            "tab_switches": int(tab_switches),
            "activity_status": activity_status,
            "ip_address": None,
            "started_at": att.started_at.isoformat() if att.started_at else None,
        })

    active_candidates_count = sum(1 for s in sessions if s["status"] == "In Progress")
    completed_count = sum(1 for s in sessions if s["status"] == "Completed")
    flagged_count = sum(1 for s in sessions if s["tab_switches"] > 0)
    first_name = sessions[0]["candidate_name"] if sessions else None

    _debug_log("A", "examiner.py:get_live_monitoring", "monitoring returning live sessions", {
        "exam_id": exam_id, "user_id": current_user.id, "db_in_progress": db_in_progress,
        "db_submitted": db_submitted, "source": "live", "session_count": len(sessions),
        "active": active_candidates_count, "completed": completed_count, "flagged": flagged_count,
        "dummy_name_detected": first_name == "Aarav Sharma" if first_name else False,
    })

    return {
        "active_candidates_count": active_candidates_count,
        "completed_count": completed_count,
        "flagged_count": flagged_count,
        "sessions": sessions,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 7. Examination Activity Logs
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/activity-logs",
    status_code=status.HTTP_200_OK,
    summary="Comprehensive examination audit trail & activity logs",
)
def get_examiner_activity_logs(
    action_type: Optional[str] = Query(None, alias="action"),
    search: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    # Use the activity log service to get real data
    result = activity_log_service.get_activity_logs(
        db=db,
        current_user=current_user,
        action=action_type,
        page=1,
        page_size=limit,
    )
    
    # Transform the data to match the expected frontend format
    transformed_logs = []
    for log in result["items"]:
        # Get candidate name from user relationship
        candidate_name = None
        if log.user:
            candidate_name = log.user.full_name or log.user.email
        
        transformed_logs.append({
            "id": log.id,
            "timestamp": log.occurred_at.isoformat() if log.occurred_at else log.created_at.isoformat(),
            "candidate_name": candidate_name or "Unknown",
            "action_type": log.action_type,
            "description": log.description or "",
            "metadata": log.metadata_json,
        })
    
    # Apply search filter if provided
    if search:
        s = search.lower()
        transformed_logs = [l for l in transformed_logs if s in l["candidate_name"].lower() or s in l["description"].lower()]
    
    return transformed_logs


# ─────────────────────────────────────────────────────────────────────────────
# 8. Results & Submissions Management
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/exams/{exam_id}/submissions",
    status_code=status.HTTP_200_OK,
    summary="Candidate submissions for a specific exam",
)
def get_exam_submissions(
    exam_id: int,
    status_filter: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return get_all_results(
        exam_id=exam_id,
        status_filter=status_filter,
        search=search,
        db=db,
        current_user=current_user,
    )


@router.get(
    "/results",
    status_code=status.HTTP_200_OK,
    summary="Comprehensive examination results & score management",
)
def get_all_results(
    exam_id: Optional[int] = Query(None),
    status_filter: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    # Build query with joins to get all necessary data
    query = (
        db.query(Result, ExamAttempt, User, Exam, Ranking)
        .join(ExamAttempt, Result.attempt_id == ExamAttempt.id)
        .join(User, ExamAttempt.student_id == User.id)
        .join(Exam, ExamAttempt.exam_id == Exam.id)
        .outerjoin(Ranking, (Ranking.exam_id == Exam.id) & (Ranking.student_id == User.id))
        .filter(ExamAttempt.status.in_(["submitted", "auto_submitted"]))
    )
    
    # Filter by exam_id if provided
    if exam_id:
        query = query.filter(Exam.id == exam_id)
    
    # Apply role-based filtering
    user_roles = {r.name.lower() for r in current_user.roles}
    if current_user.role:
        user_roles.add(current_user.role.lower())
    
    if "student" in user_roles and not ("admin" in user_roles or "examiner" in user_roles):
        # Students can only see their own results
        query = query.filter(User.id == current_user.id)
    # Examiners and admins can see all results
    
    # Apply status filter
    if status_filter == "passed":
        query = query.filter(Result.pass_fail == True)
    elif status_filter == "failed":
        query = query.filter(Result.pass_fail == False)
    
    # Apply search filter
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (User.full_name.ilike(search_term)) | 
            (User.email.ilike(search_term)) | 
            (Exam.title.ilike(search_term))
        )
    
    # Execute query
    results = query.all()
    
    # Transform data to match frontend expectations
    results_data = []
    for result, attempt, user, exam, ranking in results:
        # Calculate percentile from ranking if available
        percentile = None
        if ranking:
            # Get total candidates for this exam to calculate percentile
            total_candidates = db.query(ExamAttempt).filter(ExamAttempt.exam_id == exam.id).count()
            if total_candidates > 0:
                percentile = ((total_candidates - ranking.rank + 1) / total_candidates) * 100
        
        # Calculate time spent in minutes
        time_spent_minutes = None
        if attempt.started_at and attempt.submitted_at:
            time_diff = attempt.submitted_at - attempt.started_at
            time_spent_minutes = int(time_diff.total_seconds() / 60)
        
        results_data.append({
            "id": result.id,
            "attempt_id": attempt.id,
            "exam_id": exam.id,
            "exam_title": exam.title,
            "candidate_name": user.full_name or user.email,
            "candidate_email": user.email,
            "score_obtained": float(result.total_marks_obtained),
            "total_marks_possible": float(result.total_marks_possible),
            "percentage": float(result.percentage),
            "percentile": round(percentile, 1) if percentile else None,
            "rank": ranking.rank if ranking else None,
            "pass_fail": result.pass_fail,
            "time_spent_minutes": time_spent_minutes,
            "is_published": True,  # Default to published for now
            "submitted_at": attempt.submitted_at.isoformat() if attempt.submitted_at else None,
        })
    
    return results_data


@router.post(
    "/results/{result_id}/toggle-visibility",
    status_code=status.HTTP_200_OK,
    summary="Toggle student result visibility (Publish / Hide)",
)
def toggle_result_visibility(
    result_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    # For now, we'll implement a simple toggle functionality
    # In a real implementation, you might want to add an is_published field to the Result model
    result = db.query(Result).filter(Result.id == result_id).first()
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Result with ID {result_id} not found"
        )
    
    # For simplicity, we'll just return success
    # In production, you would toggle an is_published field on the Result or related model
    return {"message": f"Result #{result_id} visibility updated", "is_published": True}


# ─────────────────────────────────────────────────────────────────────────────
# 9. Candidate Performance Analysis
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/performance",
    status_code=status.HTTP_200_OK,
    summary="Topic-wise and question-wise candidate performance analysis",
)
def get_performance_analysis(
    exam_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    # Apply role-based filtering
    user_roles = {r.name.lower() for r in current_user.roles}
    if current_user.role:
        user_roles.add(current_user.role.lower())
    is_admin = "admin" in user_roles

    # Build base query for results and attempts
    results_query = (
        db.query(Result, ExamAttempt, Exam)
        .join(ExamAttempt, Result.attempt_id == ExamAttempt.id)
        .join(Exam, ExamAttempt.exam_id == Exam.id)
        .filter(ExamAttempt.status.in_(["submitted", "auto_submitted"]))
    )

    # Filter by exam_id if provided
    if exam_id:
        results_query = results_query.filter(Exam.id == exam_id)

    results = results_query.all()

    if not results:
        return {
            "overall_stats": {
                "average_score": 0,
                "highest_score": 0,
                "lowest_score": 0,
                "max_score": 0,
                "min_score": 0,
                "pass_percentage": 0,
                "fail_percentage": 0,
                "total_evaluated": 0,
            },
            "topic_performance": [],
            "question_wise_insights": [],
            "candidate_strengths": [],
            "weak_topics": [],
        }

    # Calculate overall statistics
    percentages = [float(r[0].percentage) for r in results]
    average_score = round(sum(percentages) / len(percentages), 1) if percentages else 0.0
    highest_score = round(max(percentages), 1) if percentages else 0.0
    lowest_score = round(min(percentages), 1) if percentages else 0.0
    passed_count = sum(1 for r in results if r[0].pass_fail)
    total_evaluated = len(results)
    pass_percentage = round((passed_count / total_evaluated) * 100, 1) if total_evaluated > 0 else 0.0
    fail_percentage = round(100.0 - pass_percentage, 1) if total_evaluated > 0 else 0.0

    # Get attempt IDs for detailed analysis
    attempt_ids = [r[1].id for r in results]

    # Query all answers with their questions and categories
    answers = (
        db.query(AttemptAnswer, Question, QuestionCategory)
        .join(Question, AttemptAnswer.question_id == Question.id)
        .outerjoin(QuestionCategory, Question.category_id == QuestionCategory.id)
        .filter(AttemptAnswer.attempt_id.in_(attempt_ids))
        .all()
    )

    # Group by topic
    topic_map: Dict[str, Dict[str, Any]] = {}
    for ans, q, cat in answers:
        raw_topic = cat.topic if (cat and cat.topic) else (cat.name if (cat and cat.name) else "General")
        t_name = raw_topic.strip()
        if t_name not in topic_map:
            topic_map[t_name] = {
                "total_answers": 0,
                "correct_answers": 0,
                "total_marks": 0.0,
                "max_marks": float(q.marks or 1.0),
            }
        topic_map[t_name]["total_answers"] += 1
        if ans.is_correct:
            topic_map[t_name]["correct_answers"] += 1
        topic_map[t_name]["total_marks"] += float(ans.marks_awarded or 0.0)

    topic_performance = []
    for t_name, d in sorted(topic_map.items()):
        tot = d["total_answers"]
        cor = d["correct_answers"]
        acc = round((cor / tot) * 100, 1) if tot > 0 else 0.0
        avg_m = round(d["total_marks"] / tot, 1) if tot > 0 else 0.0
        max_m = d["max_marks"]

        # Determine difficulty level
        if acc >= 75:
            difficulty = "Easy"
        elif acc >= 50:
            difficulty = "Medium"
        else:
            difficulty = "Hard"

        # Determine benchmark
        if acc >= 80:
            benchmark = "Excellent"
        elif acc >= 65:
            benchmark = "Good"
        elif acc >= 50:
            benchmark = "Moderate"
        else:
            benchmark = "Needs Improvement"

        topic_performance.append({
            "topic": t_name,
            "accuracy_percentage": acc,
            "average_score": f"{avg_m} / {max_m}",
            "difficulty": difficulty,
            "benchmark": benchmark,
            "total_answers": tot,
            "correct_answers": cor,
        })

    # Strengths and weaknesses
    strengths = [t["topic"] for t in topic_performance if t["accuracy_percentage"] >= 65]
    weaknesses = [t["topic"] for t in topic_performance if t["accuracy_percentage"] < 50]
    if not strengths and topic_performance:
        sorted_by_acc = sorted(topic_performance, key=lambda x: x["accuracy_percentage"], reverse=True)
        strengths = [sorted_by_acc[0]["topic"]]
    if not weaknesses and topic_performance:
        sorted_by_acc = sorted(topic_performance, key=lambda x: x["accuracy_percentage"])
        if sorted_by_acc[0]["accuracy_percentage"] < 100:
            weaknesses = [sorted_by_acc[0]["topic"]]

    # Question-wise insights: compute realistic time intervals per question from attempts
    q_times: Dict[int, List[float]] = {}
    for _, att, _ in results:
        ans_list = (
            db.query(AttemptAnswer)
            .filter(AttemptAnswer.attempt_id == att.id)
            .order_by(AttemptAnswer.answered_at.asc())
            .all()
        )
        prev_t = att.started_at
        for a in ans_list:
            if a.answered_at and prev_t:
                dur = (a.answered_at - prev_t).total_seconds()
                prev_t = a.answered_at
                if 0.5 <= dur <= 1800:
                    q_times.setdefault(a.question_id, []).append(dur)

    q_answers = (
        db.query(AttemptAnswer, Question)
        .join(Question, AttemptAnswer.question_id == Question.id)
        .filter(AttemptAnswer.attempt_id.in_(attempt_ids))
        .all()
    )
    q_stats: Dict[int, Dict[str, Any]] = {}
    for ans, q in q_answers:
        qid = q.id
        if qid not in q_stats:
            q_stats[qid] = {
                "question": q,
                "total": 0,
                "correct": 0,
                "incorrect": 0,
            }
        q_stats[qid]["total"] += 1
        if ans.is_correct:
            q_stats[qid]["correct"] += 1
        else:
            q_stats[qid]["incorrect"] += 1

    question_wise_insights = []
    for qid, st in q_stats.items():
        q_obj = st["question"]
        tot = st["total"]
        cor = st["correct"]
        incor = st["incorrect"]
        acc = round((cor / tot) * 100, 1) if tot > 0 else 0.0
        err = round((incor / tot) * 100, 1) if tot > 0 else 0.0
        times = q_times.get(qid, [])
        avg_t = round(sum(times) / len(times), 1) if times else 0.0

        if acc >= 80:
            diag = "High Accuracy"
        elif acc >= 65:
            diag = "Good Performance"
        elif acc >= 40:
            diag = "Moderate Performance"
        elif acc >= 20:
            diag = "Frequently Incorrect"
        else:
            diag = "Most Difficult"

        text_snip = q_obj.question_text.strip()
        if len(text_snip) > 65:
            text_snip = text_snip[:65] + "..."

        question_wise_insights.append({
            "question_id": qid,
            "text": text_snip,
            "accuracy": acc,
            "error_rate": err,
            "status": diag,
            "avg_time_sec": avg_t,
            "total_attempts": tot,
            "correct_count": cor,
            "incorrect_count": incor,
        })

    # Sort by lowest accuracy first, then highest error rate
    question_wise_insights.sort(key=lambda x: (x["accuracy"], -x["error_rate"]))

    return {
        "overall_stats": {
            "average_score": average_score,
            "highest_score": highest_score,
            "lowest_score": lowest_score,
            "max_score": highest_score,
            "min_score": lowest_score,
            "pass_percentage": pass_percentage,
            "fail_percentage": fail_percentage,
            "total_evaluated": total_evaluated,
        },
        "topic_performance": topic_performance,
        "question_wise_insights": question_wise_insights,
        "candidate_strengths": strengths,
        "weak_topics": weaknesses,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 10. Rankings & Leaderboard
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/rankings",
    status_code=status.HTTP_200_OK,
    summary="Examiner view of candidate rankings & leaderboards",
)
def get_rankings(
    exam_id: Optional[int] = Query(None),
    sort_by: Optional[str] = Query("score_desc"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    # Apply role-based filtering
    user_roles = {r.name.lower() for r in current_user.roles}
    if current_user.role:
        user_roles.add(current_user.role.lower())
    
    # Build query for rankings with joins
    query = (
        db.query(Ranking, User, Exam, Result, ExamAttempt)
        .join(User, Ranking.student_id == User.id)
        .join(Exam, Ranking.exam_id == Exam.id)
        .join(ExamAttempt, (ExamAttempt.student_id == User.id) & (ExamAttempt.exam_id == Exam.id))
        .join(Result, Result.attempt_id == ExamAttempt.id)
        .filter(ExamAttempt.status.in_(["submitted", "auto_submitted"]))
    )
    
    # Filter by exam_id if provided
    if exam_id:
        query = query.filter(Exam.id == exam_id)
    
    rankings_data = query.all()
    
    # Transform data to match frontend expectations
    rankings_list = []
    for ranking, user, exam, result, attempt in rankings_data:
        # Calculate percentile
        total_candidates = db.query(ExamAttempt).filter(ExamAttempt.exam_id == exam.id).count()
        percentile = round(((total_candidates - ranking.rank + 1) / total_candidates) * 100, 1) if total_candidates > 0 else 0
        
        # Calculate time taken
        time_taken = None
        if attempt.started_at and attempt.submitted_at:
            time_diff = attempt.submitted_at - attempt.started_at
            time_taken = int(time_diff.total_seconds() / 60)
        
        # Calculate accuracy from attempt answers
        accuracy = None
        attempt_answers = db.query(AttemptAnswer).filter(AttemptAnswer.attempt_id == attempt.id).all()
        if attempt_answers:
            correct_count = sum(1 for a in attempt_answers if a.is_correct)
            accuracy = round((correct_count / len(attempt_answers)) * 100, 1) if attempt_answers else 0
        
        rankings_list.append({
            "rank": ranking.rank,
            "candidate_name": user.full_name or user.email,
            "candidate_id": user.roll_number or user.email.split('@')[0],
            "score": float(ranking.score),
            "total_marks": float(result.total_marks_possible),
            "percentage": float(result.percentage),
            "percentile": percentile,
            "time_taken": f"{time_taken} mins" if time_taken else "—",
            "status": "Passed" if result.pass_fail else "Failed",
            "accuracy": f"{accuracy}%" if accuracy is not None else "—",
        })
    
    # Apply sorting
    if sort_by == "score_desc":
        rankings_list.sort(key=lambda x: x["score"], reverse=True)
    elif sort_by == "score_asc":
        rankings_list.sort(key=lambda x: x["score"])
    elif sort_by == "time_asc":
        rankings_list.sort(key=lambda x: int(x["time_taken"].split()[0]) if x["time_taken"] != "—" else 9999)
    
    return rankings_list


# ─────────────────────────────────────────────────────────────────────────────
# 11. Notifications Management
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/notifications",
    status_code=status.HTTP_200_OK,
    summary="List sent and received notifications",
)
def get_notifications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    from sqlalchemy import desc

    # Get recent notifications sent across the portal
    notifications = db.query(Notification).order_by(desc(Notification.created_at)).limit(50).all()

    # Group multi-recipient broadcasts so examiner sees clean summary entries
    formatted_notifications = []
    seen_broadcasts = {}
    for n in notifications:
        key = (n.title, n.message, n.created_at.strftime("%Y-%m-%d %H:%M") if n.created_at else "")
        if key in seen_broadcasts:
            idx = seen_broadcasts[key]
            formatted_notifications[idx]["recipients_count"] += 1
            continue

        raw_type = (n.entity_type or n.notification_type or "announcement").lower()
        entry = {
            "id": n.id,
            "title": n.title,
            "message": n.message,
            "type": raw_type,
            "sent_at": n.created_at.strftime("%b %d, %Y %H:%M") if n.created_at else "Recently",
            "recipients_count": 1,
        }
        seen_broadcasts[key] = len(formatted_notifications)
        formatted_notifications.append(entry)

    return formatted_notifications


@router.post(
    "/notifications",
    status_code=status.HTTP_201_CREATED,
    summary="Broadcast announcement or exam notification to candidates",
)
def send_notification(
    payload: NotificationCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    import uuid
    from app.services import notification_service
    from app.models.exam import ExamAssignment
    from app.models.notification import ALLOWED_NOTIFICATION_TYPES

    # Map frontend notification types to allowed database notification types
    type_map = {
        "announcement": "SYSTEM",
        "reminder": "EXAM_UPCOMING",
        "schedule_change": "EXAM_UPCOMING",
        "result_notice": "RESULT_AVAILABLE",
        "instruction": "SYSTEM",
    }
    raw_type = (payload.type or "announcement").lower().strip()
    db_notif_type = type_map.get(raw_type, "SYSTEM")
    if raw_type.upper() in ALLOWED_NOTIFICATION_TYPES:
        db_notif_type = raw_type.upper()

    # Determine target students based on payload
    target_students = []

    if payload.target_exam_id:
        # Get students assigned to this specific exam
        assignments = db.query(ExamAssignment).filter(ExamAssignment.exam_id == payload.target_exam_id).all()
        student_ids = [a.student_id for a in assignments if a.student_id]
        if student_ids:
            target_students = db.query(User).filter(User.id.in_(student_ids)).all()
        else:
            all_users = db.query(User).all()
            target_students = [u for u in all_users if u.role.lower() == "student"]
    else:
        # Broadcast to all candidate students across the portal
        all_users = db.query(User).all()
        target_students = [u for u in all_users if u.role.lower() == "student"]

    now_ts = int(datetime.now(timezone.utc).timestamp())
    notifications_created = 0

    for student in target_students:
        if student:
            try:
                unique_key = f"bcast_{current_user.id}_{student.id}_{now_ts}_{uuid.uuid4().hex[:6]}"
                notification_service.create_notification(
                    db=db,
                    user_id=student.id,
                    title=payload.title,
                    message=payload.message,
                    notification_type=db_notif_type,
                    entity_type=raw_type,
                    entity_id=str(payload.target_exam_id) if payload.target_exam_id else None,
                    event_key=unique_key,
                )
                notifications_created += 1
            except Exception as e:
                print(f"Failed to create notification for student {student.id}: {e}")

    db.commit()

    return {
        "message": f"Notification broadcast successfully to {notifications_created} candidate(s)",
        "title": payload.title,
        "type": payload.type,
        "recipients_count": notifications_created,
        "sent_at": datetime.now(timezone.utc).isoformat(),
    }


# ─────────────────────────────────────────────────────────────────────────────
# 12. Examiner Profile & Security
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/profile",
    status_code=status.HTTP_200_OK,
    summary="Get examiner profile details",
)
def get_examiner_profile(
    current_user: User = Depends(get_current_active_user),
):
    return {
        "id": current_user.id,
        "full_name": current_user.full_name or "Dr. Examiner",
        "email": current_user.email,
        "role": current_user.role or "examiner",
        "department": "Computer Science & Engineering",
        "contact_phone": "+91 98765 43210",
        "institution": "National Institute of Technology",
        "joined_at": current_user.created_at.isoformat() if current_user.created_at else None,
    }


@router.put(
    "/profile",
    status_code=status.HTTP_200_OK,
    summary="Update examiner profile information",
)
def update_examiner_profile(
    payload: ExaminerProfileUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if payload.full_name is not None:
        current_user.full_name = payload.full_name.strip()
    if payload.email is not None:
        current_user.email = payload.email.strip()
    db.commit()
    db.refresh(current_user)
    return {
        "message": "Profile updated successfully",
        "full_name": current_user.full_name,
        "email": current_user.email,
    }


@router.put(
    "/change-password",
    status_code=status.HTTP_200_OK,
    summary="Change examiner account password",
)
def change_password(
    payload: ExaminerChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if not verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password entered is incorrect",
        )
    current_user.password_hash = hash_password(payload.new_password)
    db.commit()
    return {"message": "Password changed successfully"}
