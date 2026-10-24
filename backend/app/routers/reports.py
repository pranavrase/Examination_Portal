"""
Module 2.12 — Reports Router
============================
Endpoints for exam, student, question, and candidate performance reporting.

Endpoints:
  GET /reports/my-performance           — Student: View own examination performance across all exams
  GET /reports/exams/{exam_id}          — Examiner/Admin: Performance overview and score statistics for an exam
  GET /reports/exams/{exam_id}/questions — Examiner/Admin: Question-level attempt and accuracy analysis
  GET /reports/students/{student_id}    — Examiner/Admin (or self): Comprehensive student performance report
  GET /reports/candidate-wise           — Examiner/Admin: Candidate-wise aggregated exam results with filters
  GET /reports/topic-wise               — Examiner/Admin: Topic/category-level accuracy and score aggregation
  GET /reports/export                   — Examiner/Admin: Export candidate performance report as CSV
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, get_current_active_user
from app.models.user import User
from app.schemas.report import (
    ExamPerformanceReport,
    StudentPerformanceReport,
    ExamQuestionsReport,
    CandidateWiseReportResponse,
    TopicWiseReportResponse,
)
from app.services import report_service

router = APIRouter(prefix="/reports", tags=["Reports & Analytics — Module 2.12"])


@router.get(
    "/my-performance",
    response_model=StudentPerformanceReport,
    status_code=status.HTTP_200_OK,
    summary="Get authenticated student's performance report",
    responses={
        200: {"description": "Student's examination report returned successfully"},
        401: {"description": "Missing or invalid JWT token"},
    },
)
def get_my_performance(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Retrieve performance report across all completed exams for the authenticated student.
    Never relies on client-provided student IDs.
    """
    return report_service.get_my_performance_report(
        db=db,
        current_user=current_user,
    )


@router.get(
    "/exams/{exam_id}",
    response_model=ExamPerformanceReport,
    status_code=status.HTTP_200_OK,
    summary="Get exam performance report (Examiner / Admin)",
    responses={
        200: {"description": "Exam performance report returned successfully"},
        401: {"description": "Missing or invalid JWT token"},
        403: {"description": "Forbidden — user not authorized for this exam"},
        404: {"description": "Exam not found"},
    },
)
def get_exam_performance(
    exam_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Retrieve aggregated metrics for an examination:
      - Total attempts & students
      - Completed & in-progress attempts
      - Passed & failed student counts
      - Average, highest, and lowest scores
      - Average percentage
    """
    return report_service.get_exam_performance_report(
        exam_id=exam_id,
        db=db,
        current_user=current_user,
    )


@router.get(
    "/exams/{exam_id}/questions",
    response_model=ExamQuestionsReport,
    status_code=status.HTTP_200_OK,
    summary="Get question-level performance report (Examiner / Admin)",
    responses={
        200: {"description": "Question performance report returned successfully"},
        401: {"description": "Missing or invalid JWT token"},
        403: {"description": "Forbidden — user not authorized for this exam"},
        404: {"description": "Exam not found"},
    },
)
def get_exam_questions_performance(
    exam_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Retrieve question-level performance statistics:
      - Total attempts per question
      - Correct & incorrect answer counts
      - Unanswered candidate count
      - Accuracy percentage
    """
    return report_service.get_exam_questions_report(
        exam_id=exam_id,
        db=db,
        current_user=current_user,
    )


@router.get(
    "/students/{student_id}",
    response_model=StudentPerformanceReport,
    status_code=status.HTTP_200_OK,
    summary="Get student performance report (Examiner / Admin or Self)",
    responses={
        200: {"description": "Student performance report returned successfully"},
        401: {"description": "Missing or invalid JWT token"},
        403: {"description": "Forbidden — students cannot access other students' reports"},
        404: {"description": "Student not found"},
    },
)
def get_student_performance(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Retrieve examination performance summary for a specific student.
    Students may only request their own ID; examiners and admins can view authorized records.
    """
    return report_service.get_student_performance_report(
        student_id=student_id,
        db=db,
        current_user=current_user,
    )


@router.get(
    "/candidate-wise",
    response_model=CandidateWiseReportResponse,
    status_code=status.HTTP_200_OK,
    summary="Get candidate-wise report with filtering and pagination (Examiner / Admin)",
    responses={
        200: {"description": "Candidate-wise report returned successfully"},
        401: {"description": "Missing or invalid JWT token"},
        403: {"description": "Forbidden — students cannot access candidate reports"},
    },
)
def get_candidate_wise_report(
    exam_id: Optional[int] = Query(None, description="Filter by Exam ID"),
    topic: Optional[str] = Query(None, description="Filter by Topic"),
    candidate: Optional[str] = Query(None, description="Search candidate by name or email"),
    from_date: Optional[str] = Query(None, description="Filter attempts from date (YYYY-MM-DD or ISO)"),
    to_date: Optional[str] = Query(None, description="Filter attempts to date (YYYY-MM-DD or ISO)"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(15, ge=1, le=100, description="Page size limit"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Retrieve candidate-wise performance listings with search, date-range filtering, and pagination.
    """
    return report_service.get_candidate_wise_report(
        exam_id=exam_id,
        topic=topic,
        candidate=candidate,
        from_date=from_date,
        to_date=to_date,
        page=page,
        limit=limit,
        db=db,
        current_user=current_user,
    )


@router.get(
    "/topic-wise",
    response_model=TopicWiseReportResponse,
    status_code=status.HTTP_200_OK,
    summary="Get topic-wise performance report (Examiner / Admin)",
    responses={
        200: {"description": "Topic-wise report returned successfully"},
        401: {"description": "Missing or invalid JWT token"},
        403: {"description": "Forbidden — students cannot access topic reports"},
    },
)
def get_topic_wise_report(
    exam_id: Optional[int] = Query(None, description="Filter by Exam ID"),
    topic: Optional[str] = Query(None, description="Filter by Topic keyword"),
    from_date: Optional[str] = Query(None, description="Filter attempts from date"),
    to_date: Optional[str] = Query(None, description="Filter attempts to date"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Retrieve aggregated topic/category performance report for examinations.
    """
    return report_service.get_topic_wise_report(
        exam_id=exam_id,
        topic=topic,
        from_date=from_date,
        to_date=to_date,
        db=db,
        current_user=current_user,
    )


@router.get(
    "/export",
    status_code=status.HTTP_200_OK,
    summary="Export performance report as CSV (Examiner / Admin)",
    responses={
        200: {"description": "CSV export file returned", "content": {"text/csv": {}}},
        401: {"description": "Missing or invalid JWT token"},
        403: {"description": "Forbidden — students cannot export candidate reports"},
    },
)
def export_report(
    exam_id: Optional[int] = Query(None, description="Filter by Exam ID"),
    topic: Optional[str] = Query(None, description="Filter by Topic"),
    candidate: Optional[str] = Query(None, description="Search candidate name or email"),
    from_date: Optional[str] = Query(None, description="Filter from date"),
    to_date: Optional[str] = Query(None, description="Filter to date"),
    format: str = Query("csv", description="Export format: 'csv'"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Stream a filtered candidate performance report as a downloadable CSV file.
    """
    csv_content = report_service.export_report_csv(
        exam_id=exam_id,
        topic=topic,
        candidate=candidate,
        from_date=from_date,
        to_date=to_date,
        db=db,
        current_user=current_user,
    )

    filename = f"report_exam_{exam_id}.csv" if exam_id else "exam_performance_report.csv"

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
