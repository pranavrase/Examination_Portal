from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from pydantic import BaseModel, EmailStr, Field

from app.core.dependencies import get_db, get_current_active_user, require_role
from app.models.user import User
from app.models.exam import Exam, ExamAssignment
from app.models.attempt import ExamAttempt
from app.models.result import Result, Ranking
from app.models.question import Question, QuestionCategory, ExamQuestion
from app.services import exam_service
from app.services.auth_service import authenticate_user

router = APIRouter(
    prefix="/students",
    tags=["Student Portal"],
    dependencies=[Depends(require_role(["student", "examiner", "admin"]))],
)


# Pydantic schemas for profile and password updates
class ProfileUpdateRequest(BaseModel):
    full_name: str = Field(..., min_length=2, description="Full name of the student")
    phone: Optional[str] = Field(None, description="Phone number")
    roll_number: Optional[str] = Field(None, description="Student ID / Roll number")
    college: Optional[str] = Field(None, description="College / Department")


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(..., description="Current password for verification")
    new_password: str = Field(..., min_length=8, description="New password must be at least 8 characters long")


@router.get("/{student_id}/exams", status_code=status.HTTP_200_OK)
def get_student_assigned_exams(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Fetch all exams assigned to the student via exam_assignments table.
    Includes completed exams from exam_attempts.
    Falls back to all published exams if no assignments found.
    """
    assignments = (
        db.query(ExamAssignment)
        .filter(ExamAssignment.student_id == student_id)
        .all()
    )

    assigned_exam_ids = set()
    exams_list = []
    for assign in assignments:
        exam = assign.exam
        if not exam:
            continue
        assigned_exam_ids.add(exam.id)
        settings = exam.settings
        
        # Check if student has completed this exam
        attempt = db.query(ExamAttempt).filter(
            ExamAttempt.exam_id == exam.id,
            ExamAttempt.student_id == student_id,
            ExamAttempt.status.in_(["submitted", "auto_submitted"])
        ).first()
        
        exam_status = "completed" if attempt else ("available" if exam.status == "published" else exam.status)
        
        # Derive subject/topic from question categories
        categories = (
            db.query(QuestionCategory.name, QuestionCategory.topic)
            .join(Question, Question.category_id == QuestionCategory.id)
            .join(ExamQuestion, ExamQuestion.question_id == Question.id)
            .filter(ExamQuestion.exam_id == exam.id)
            .distinct()
            .all()
        )
        
        subject = None
        category = None
        topic = None
        
        if categories:
            category_names = [cat[0].lower() for cat in categories]
            if any('aptitude' in name for name in category_names):
                subject = "Aptitude"
                category = "Aptitude"
            elif any('reasoning' in name for name in category_names):
                subject = "Reasoning"
                category = "Reasoning"
            elif any('technical' in name for name in category_names):
                subject = "Technical"
                category = "Technical"
            elif any('coding' in name for name in category_names):
                subject = "Coding"
                category = "Coding"
            else:
                subject = categories[0][0] if categories[0][0] else "General"
                category = ", ".join([cat[0] for cat in categories[:2]]) if len(categories) > 1 else categories[0][0]
            
            topic = categories[0][1] if categories[0][1] else "Core Evaluation"
        
        exams_list.append({
            "id": exam.id,
            "title": exam.title,
            "description": exam.description or "",
            "status": exam_status,
            "subject": subject or "Technical & Aptitude",
            "category": category or "Aptitude, Reasoning & Coding",
            "type": subject or "General",
            "topic": topic or "Core Evaluation",
            "duration_minutes": settings.duration_minutes if settings else None,
            "total_marks": float(settings.total_marks) if settings else None,
            "passing_percentage": float(settings.passing_percentage) if settings else None,
            "negative_marking": float(settings.negative_marking_ratio) if settings else None,
            "scheduled_start": assign.scheduled_start.isoformat() if assign.scheduled_start else datetime.now(timezone.utc).isoformat(),
            "scheduled_end": assign.scheduled_end.isoformat() if assign.scheduled_end else None,
            "assigned_at": assign.assigned_at.isoformat() if assign.assigned_at else None,
            "attempt_id": attempt.id if attempt else None,
        })

    # In addition to direct assignments, include all published exams open to students
    published_query = db.query(Exam).filter(Exam.status == "published")
    if assigned_exam_ids:
        published_query = published_query.filter(~Exam.id.in_(assigned_exam_ids))
    published = published_query.all()

    for exam in published:
        settings = exam.settings
        
        # Check if student has completed this exam
        attempt = db.query(ExamAttempt).filter(
            ExamAttempt.exam_id == exam.id,
            ExamAttempt.student_id == student_id,
            ExamAttempt.status.in_(["submitted", "auto_submitted"])
        ).first()
        
        exam_status = "completed" if attempt else "available"
        
        # Derive subject/topic from question categories
        categories = (
            db.query(QuestionCategory.name, QuestionCategory.topic)
            .join(Question, Question.category_id == QuestionCategory.id)
            .join(ExamQuestion, ExamQuestion.question_id == Question.id)
            .filter(ExamQuestion.exam_id == exam.id)
            .distinct()
            .all()
        )
        
        subject = None
        category = None
        topic = None
        
        if categories:
            category_names = [cat[0].lower() for cat in categories]
            if any('aptitude' in name for name in category_names):
                subject = "Aptitude"
                category = "Aptitude"
            elif any('reasoning' in name for name in category_names):
                subject = "Reasoning"
                category = "Reasoning"
            elif any('technical' in name for name in category_names):
                subject = "Technical"
                category = "Technical"
            elif any('coding' in name for name in category_names):
                subject = "Coding"
                category = "Coding"
            else:
                subject = categories[0][0] if categories[0][0] else "General"
                category = ", ".join([cat[0] for cat in categories[:2]]) if len(categories) > 1 else categories[0][0]
            
            topic = categories[0][1] if categories[0][1] else "Core Evaluation"
        
        exams_list.append({
            "id": exam.id,
            "title": exam.title,
            "description": exam.description or "Comprehensive academic assessment.",
            "status": exam_status,
            "subject": subject or "Technical & Aptitude",
            "category": category or "Aptitude, Reasoning & Coding",
            "type": subject or "General",
            "topic": topic or "Core Evaluation",
            "duration_minutes": settings.duration_minutes if settings else None,
            "total_marks": float(settings.total_marks) if settings else None,
            "passing_percentage": float(settings.passing_percentage) if settings else None,
            "negative_marking": float(settings.negative_marking_ratio) if settings else None,
            "scheduled_start": datetime.now(timezone.utc).isoformat(),
            "scheduled_end": None,
            "assigned_at": exam.created_at.isoformat() if exam.created_at else datetime.now(timezone.utc).isoformat(),
            "attempt_id": attempt.id if attempt else None,
        })

    return exams_list


@router.get("/{student_id}/results", status_code=status.HTTP_200_OK)
def get_student_exam_results(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Fetch all completed exam results and scorecards for the student.
    """
    db_results = (
        db.query(Result)
        .join(ExamAttempt, Result.attempt_id == ExamAttempt.id)
        .filter(ExamAttempt.student_id == student_id)
        .order_by(desc(Result.created_at))
        .all()
    )

    results_list = []
    for res in db_results:
        attempt = db.query(ExamAttempt).filter(ExamAttempt.id == res.attempt_id).first()
        exam = attempt.exam if attempt else None
        results_list.append({
            "id": res.id,
            "attempt_id": res.attempt_id,
            "exam_id": exam.id if exam else None,
            "exam_title": exam.title if exam else "General Assessment",
            "subject": "Core Assessment",
            "score_obtained": float(res.total_marks_obtained),
            "total_marks": float(res.total_marks_possible),
            "percentage": float(res.percentage),
            "is_passed": res.pass_fail,
            "rank": "#1",
            "submitted_at": attempt.submitted_at.isoformat() if attempt and attempt.submitted_at else res.created_at.isoformat(),
        })

    return results_list


@router.get("/exams/{exam_id}", status_code=status.HTTP_200_OK)
def get_student_exam_detail(
    exam_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Fetch single exam details for student lobby and exam session.
    Includes existing attempt status and completion flag.
    """
    exam_obj = exam_service.get_exam_by_id(
        db=db,
        exam_id=exam_id,
        current_user=current_user,
    )
    
    # Check attempt for current student
    attempt = db.query(ExamAttempt).filter(
        ExamAttempt.exam_id == exam_id,
        ExamAttempt.student_id == current_user.id,
    ).first()

    settings = exam_obj.settings
    return {
        "id": exam_obj.id,
        "title": exam_obj.title,
        "description": exam_obj.description or "",
        "instructions": getattr(exam_obj, "instructions", None),
        "status": exam_obj.status,
        "duration_minutes": settings.duration_minutes if settings else None,
        "duration": settings.duration_minutes if settings else None,
        "total_marks": float(settings.total_marks) if settings else None,
        "passing_percentage": float(settings.passing_percentage) if settings else None,
        "negative_marking": float(settings.negative_marking_ratio) if settings else None,
        "created_by": exam_obj.created_by,
        "settings": {
            "duration_minutes": settings.duration_minutes if settings else None,
            "total_marks": float(settings.total_marks) if settings else None,
            "passing_percentage": float(settings.passing_percentage) if settings else None,
            "negative_marking_ratio": float(settings.negative_marking_ratio) if settings else None,
        } if settings else None,
        "attempt_id": attempt.id if attempt else None,
        "attempt_status": attempt.status if attempt else None,
        "is_completed": (attempt.status in ("submitted", "auto_submitted")) if attempt else False,
    }


@router.get("/leaderboard", status_code=status.HTTP_200_OK)
def get_student_leaderboard(
    exam_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get overall leaderboard for students with anonymized peer data.
    If exam_id is provided, returns leaderboard for specific exam.
    Otherwise returns overall rankings across all exams.
    """
    if exam_id:
        # Get leaderboard for specific exam
        rankings = (
            db.query(Ranking)
            .join(Exam, Ranking.exam_id == Exam.id)
            .filter(Ranking.exam_id == exam_id)
            .order_by(Ranking.rank.asc())
            .all()
        )
        
        exam = db.query(Exam).filter(Exam.id == exam_id).first()
        if not exam:
            raise HTTPException(status_code=404, detail="Exam not found")
    else:
        # Get overall leaderboard across all exams (best performance per student)
        # This aggregates the best score/rank per student across all exams
        student_best_rankings = (
            db.query(
                Ranking.student_id,
                func.max(Ranking.score).label('best_score'),
                func.min(Ranking.rank).label('best_rank'),
            )
            .group_by(Ranking.student_id)
            .all()
        )
        
        if not student_best_rankings:
            return {
                "exam_id": None,
                "exam_title": "Overall Rankings",
                "total_candidates": 0,
                "rankings": []
            }
        
        # Get full ranking records for the best performance of each student
        ranking_ids = []
        for student_id, best_score, best_rank in student_best_rankings:
            best_ranking = (
                db.query(Ranking)
                .filter(
                    Ranking.student_id == student_id,
                    Ranking.score == best_score,
                    Ranking.rank == best_rank
                )
                .first()
            )
            if best_ranking:
                ranking_ids.append(best_ranking.id)
        
        rankings = (
            db.query(Ranking)
            .filter(Ranking.id.in_(ranking_ids))
            .order_by(Ranking.rank.asc())
            .all()
        )
    
    # Build leaderboard items with anonymized data for privacy
    leaderboard_items = []
    for ranking in rankings:
        student = ranking.student or db.query(User).filter(User.id == ranking.student_id).first()
        
        # Get additional details from attempts
        attempt = (
            db.query(ExamAttempt)
            .filter(
                ExamAttempt.exam_id == ranking.exam_id,
                ExamAttempt.student_id == ranking.student_id,
                ExamAttempt.status.in_(["submitted", "auto_submitted"])
            )
            .first()
        )
        
        result = None
        if attempt:
            result = db.query(Result).filter(Result.attempt_id == attempt.id).first()
        
        # Calculate completion time
        completion_time = None
        if attempt and attempt.started_at and attempt.submitted_at:
            duration = attempt.submitted_at - attempt.started_at
            minutes = int(duration.total_seconds() / 60)
            completion_time = f"{minutes} mins"
        
        # Calculate accuracy (based on percentage)
        accuracy = None
        if result and result.percentage:
            accuracy = f"{result.percentage:.0f}%"
        
        # Calculate percentile
        total_candidates = len(rankings)
        percentile = 0
        if total_candidates > 0:
            percentile = round(((total_candidates - ranking.rank + 1) / total_candidates) * 100, 1)
        
        leaderboard_items.append({
            "rank": ranking.rank,
            "student_id": ranking.student_id,
            "name": student.full_name if student else f"Student {ranking.student_id}",
            "roll": student.email.split('@')[0] if student and student.email else f"ID-{ranking.student_id}",
            "score": float(ranking.score),
            "percentile": percentile,
            "accuracy": accuracy,
            "time": completion_time,
            "is_me": ranking.student_id == current_user.id,
            "exam_id": ranking.exam_id,
        })
    
    return {
        "exam_id": exam_id,
        "exam_title": exam.title if exam_id else "Overall Rankings",
        "total_candidates": len(leaderboard_items),
        "rankings": leaderboard_items
    }


@router.get("/profile", status_code=status.HTTP_200_OK)
def get_student_profile(
    current_user: User = Depends(get_current_active_user),
):
    """
    Get current student profile details.
    """
    return {
        "id": current_user.id,
        "full_name": current_user.full_name or "Student",
        "email": current_user.email,
        "role": current_user.role or "student",
        "phone": getattr(current_user, 'phone', None),
        "roll_number": getattr(current_user, 'roll_number', None),
        "college": getattr(current_user, 'college', None),
        "created_at": current_user.created_at.isoformat() if current_user.created_at else None,
    }


@router.put("/profile", status_code=status.HTTP_200_OK)
def update_student_profile(
    profile_data: ProfileUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Update student profile information.
    """
    # Update user fields
    current_user.full_name = profile_data.full_name
    
    # Update custom fields - the User model now has these fields
    try:
        current_user.phone = profile_data.phone
        current_user.roll_number = profile_data.roll_number
        current_user.college = profile_data.college
    except AttributeError:
        # If columns don't exist in database yet, handle gracefully
        pass
    
    current_user.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    
    try:
        db.commit()
        db.refresh(current_user)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update profile: {str(e)}"
        )
    
    return {
        "id": current_user.id,
        "full_name": current_user.full_name,
        "email": current_user.email,
        "phone": getattr(current_user, 'phone', None),
        "roll_number": getattr(current_user, 'roll_number', None),
        "college": getattr(current_user, 'college', None),
        "message": "Profile updated successfully"
    }


@router.post("/change-password", status_code=status.HTTP_200_OK)
def change_student_password(
    password_data: PasswordChangeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Change student password after verifying current password.
    """
    # Verify current password
    try:
        authenticate_user(
            db=db,
            email=current_user.email,
            password=password_data.current_password
        )
    except HTTPException:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # Hash new password and update
    from app.core.security import hash_password
    current_user.password_hash = hash_password(password_data.new_password)
    current_user.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    
    try:
        db.commit()
        db.refresh(current_user)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update password: {str(e)}"
        )
    
    return {
        "message": "Password changed successfully"
    }
