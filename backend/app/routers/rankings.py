"""
Module 2.11 — Rankings Router
==============================
Endpoints:
  GET  /exams/{exam_id}/leaderboard       — Examiner (own exam) / Admin: Full leaderboard
  GET  /exams/{exam_id}/my-rank           — Authenticated candidate: View own rank & percentile
  POST /exams/{exam_id}/rankings/compute  — Examiner / Admin: Trigger ranking computation
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, get_current_active_user, require_role
from app.models.user import User
from app.schemas.ranking import (
    LeaderboardResponse,
    MyRankResponse,
    RankingComputeResponse,
)
from app.services import ranking_service

router = APIRouter(tags=["Rankings & Leaderboard — Module 2.11"])


@router.get(
    "/exams/{exam_id}/leaderboard",
    response_model=LeaderboardResponse,
    status_code=status.HTTP_200_OK,
    summary="Get full leaderboard for an exam (Examiner / Admin)",
    responses={
        200: {"description": "Complete exam leaderboard returned successfully"},
        401: {"description": "Missing or invalid JWT token"},
        403: {"description": "Forbidden — students cannot view full leaderboard; examiners only own exams"},
        404: {"description": "Exam not found"},
    },
)
@router.get(
    "/exams/{exam_id}/rankings",
    response_model=LeaderboardResponse,
    status_code=status.HTTP_200_OK,
    summary="Get full leaderboard for an exam (Alias for /leaderboard)",
)
def get_exam_leaderboard(
    exam_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Return the complete ranking leaderboard for an examination.

    Authorization:
      - **Admin** → Can access any exam leaderboard
      - **Examiner** → Can access leaderboards for exams they created
      - **Student** → Forbidden (403); must use `/exams/{exam_id}/my-rank`
    """
    return ranking_service.get_leaderboard(
        exam_id=exam_id,
        db=db,
        current_user=current_user,
    )


@router.get(
    "/exams/{exam_id}/my-rank",
    response_model=MyRankResponse,
    status_code=status.HTTP_200_OK,
    summary="Get student's own rank and percentile standing",
    responses={
        200: {"description": "Candidate rank returned successfully"},
        401: {"description": "Missing or invalid JWT token"},
        404: {"description": "Exam not found or student has not submitted attempt"},
    },
)
def get_student_rank(
    exam_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Return the authenticated student's individual rank, score, and percentile standing.
    Sensitive details of peers are not exposed.
    """
    return ranking_service.get_my_rank(
        exam_id=exam_id,
        db=db,
        current_user=current_user,
    )


@router.post(
    "/exams/{exam_id}/rankings/compute",
    response_model=RankingComputeResponse,
    status_code=status.HTTP_200_OK,
    summary="(Re-)compute rankings for an exam (Examiner / Admin)",
    dependencies=[Depends(require_role(["admin", "examiner"]))],
    responses={
        200: {"description": "Rankings computed and persisted successfully"},
        401: {"description": "Missing or invalid JWT token"},
        403: {"description": "Forbidden — requires Examiner or Admin role"},
        404: {"description": "Exam not found"},
    },
)
def compute_rankings(
    exam_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Trigger deterministic ranking computation for an examination.
    Safe to execute repeatedly (idempotent).
    """
    # If examiner, verify ownership
    user_roles = {r.name.lower() for r in current_user.roles}
    if current_user.role:
        user_roles.add(current_user.role.lower())

    if "admin" not in user_roles and "examiner" in user_roles:
        from app.models.exam import Exam
        from fastapi import HTTPException
        exam = db.query(Exam).filter(Exam.id == exam_id).first()
        if not exam:
            raise HTTPException(status_code=404, detail=f"Exam {exam_id} not found")
        if exam.created_by != current_user.id:
            raise HTTPException(status_code=403, detail="Examiners can only compute rankings for their own exams")

    rankings = ranking_service.compute_rankings_for_exam(exam_id=exam_id, db=db)
    return RankingComputeResponse(
        success=True,
        exam_id=exam_id,
        total_ranked=len(rankings),
        message=f"Successfully computed rankings for {len(rankings)} candidates",
    )
