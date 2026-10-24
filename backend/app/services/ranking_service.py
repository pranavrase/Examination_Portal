"""
Module 2.11 — Ranking Engine Service
====================================
Service functions:
  - compute_rankings_for_exam(exam_id, db) -> List[Ranking]
  - get_leaderboard(exam_id, db, current_user) -> LeaderboardResponse
  - get_my_rank(exam_id, db, current_user) -> MyRankResponse

Design Principles:
  * Deterministic ranking:
      1. Score DESC (higher score ranks better)
      2. Submission Time ASC (earlier submission ranks better)
      3. Duration Taken ASC (less time taken ranks better)
      4. Student ID ASC (deterministic tie resolution)
  * Derived data source: consumes Module 2.10 Result records as source of truth.
  * Idempotency: safe to run repeatedly without creating duplicate rows.
  * Atomicity: transactional writes with rollback on failure.
  * Role-based security: students view own rank; examiners/admins view leaderboard.
"""

from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import List, Optional, Dict, Any, Tuple
from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.models.exam import Exam
from app.models.attempt import ExamAttempt
from app.models.result import Result, Ranking
from app.models.user import User
from app.schemas.ranking import (
    RankingItemResponse,
    LeaderboardResponse,
    MyRankResponse,
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _user_roles(user: User) -> set:
    roles = {r.name.lower() for r in user.roles}
    if user.role:
        roles.add(user.role.lower())
    return roles


def _is_admin(user: User) -> bool:
    return "admin" in _user_roles(user)


def _is_examiner(user: User) -> bool:
    return "examiner" in _user_roles(user)


def _is_student(user: User) -> bool:
    return "student" in _user_roles(user)


def format_duration(td: Optional[timedelta]) -> Optional[str]:
    """Format timedelta duration into a user-friendly string."""
    if td is None:
        return None
    total_seconds = max(0, int(td.total_seconds()))
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60

    if hours > 0:
        return f"{hours}h {minutes}m {seconds}s"
    if minutes > 0:
        return f"{minutes}m {seconds}s"
    return f"{seconds}s"


def compute_rankings_for_exam(exam_id: int, db: Session) -> List[Ranking]:
    """
    Compute or recompute rankings for all eligible finalized attempts of an exam.

    Responsibilities:
      1. Verify exam exists.
      2. Load all finalized attempts ('submitted', 'auto_submitted') with valid Result.
      3. Sort candidates deterministically:
           - score DESC
           - submitted_at ASC
           - duration ASC
           - student_id ASC
      4. Assign 1-indexed ranks (1, 2, 3, ...).
      5. Upsert Ranking rows idempotently.
      6. Return persisted Ranking records ordered by rank.
    """
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Exam {exam_id} not found",
        )

    # Query finalized attempts with calculated results
    records: List[Tuple[Result, ExamAttempt]] = (
        db.query(Result, ExamAttempt)
        .join(ExamAttempt, Result.attempt_id == ExamAttempt.id)
        .filter(
            ExamAttempt.exam_id == exam_id,
            ExamAttempt.status.in_(["submitted", "auto_submitted"]),
        )
        .all()
    )

    if not records:
        # If no results exist, remove any stale rankings and return empty list
        db.query(Ranking).filter(Ranking.exam_id == exam_id).delete()
        db.commit()
        try:
            from app.services.activity_log_service import log_activity
            log_activity(
                db=db,
                action="ranking_generated",
                entity_type="exam",
                entity_id=str(exam_id),
                description=f"Leaderboard rankings computed for Exam #{exam_id} (0 candidates)",
                metadata={"exam_id": exam_id, "candidates_count": 0},
                commit=True,
            )
        except Exception:
            pass
        return []

    candidates = []
    for res, att in records:
        score_val = float(res.total_marks_obtained)
        sub_time = att.submitted_at or att.updated_at or utc_now()
        start_time = att.started_at or sub_time
        duration = sub_time - start_time if sub_time >= start_time else timedelta(0)

        candidates.append({
            "student_id": att.student_id,
            "score": score_val,
            "submitted_at": sub_time,
            "duration": duration,
        })

    # Deterministic sorting:
    # 1. Higher score = better rank (descending)
    # 2. Earlier submission time = better rank (ascending)
    # 3. Less duration taken = better rank (ascending)
    # 4. Student ID = deterministic final tie-breaker (ascending)
    candidates.sort(key=lambda c: (
        -c["score"],
        c["submitted_at"],
        c["duration"],
        c["student_id"],
    ))

    now = utc_now()
    existing_rankings = {
        r.student_id: r
        for r in db.query(Ranking).filter(Ranking.exam_id == exam_id).all()
    }

    current_student_ids = set()
    ranked_records: List[Ranking] = []

    try:
        for idx, cand in enumerate(candidates, start=1):
            s_id = cand["student_id"]
            current_student_ids.add(s_id)
            score_decimal = Decimal(str(cand["score"]))
            duration_val = cand["duration"]

            if s_id in existing_rankings:
                rec = existing_rankings[s_id]
                rec.rank = idx
                rec.score = score_decimal
                rec.tie_break_time = duration_val
                rec.updated_at = now
                ranked_records.append(rec)
            else:
                rec = Ranking(
                    exam_id=exam_id,
                    student_id=s_id,
                    rank=idx,
                    score=score_decimal,
                    tie_break_time=duration_val,
                    created_at=now,
                    updated_at=now,
                )
                db.add(rec)
                ranked_records.append(rec)

        # Remove rankings for students who are no longer eligible
        for s_id, rec in existing_rankings.items():
            if s_id not in current_student_ids:
                db.delete(rec)

        db.commit()

        # Log ranking_generated activity (Module 2.13)
        try:
            from app.services.activity_log_service import log_activity
            log_activity(
                db=db,
                action="ranking_generated",
                entity_type="exam",
                entity_id=str(exam_id),
                description=f"Leaderboard rankings computed for Exam #{exam_id} ({len(candidates)} candidates)",
                metadata={"exam_id": exam_id, "candidates_count": len(candidates)},
                commit=True,
            )
        except Exception:
            pass

        # Notify ranked students (Module 2.15)
        try:
            from app.services.notification_service import create_notification
            for cand in candidates:
                s_id = cand["student_id"]
                create_notification(
                    db=db,
                    user_id=s_id,
                    title="Ranking Available",
                    message="Your examination ranking is now available.",
                    notification_type="RANKING_AVAILABLE",
                    entity_type="ranking",
                    entity_id=str(exam_id),
                    event_key=f"ranking_exam_{exam_id}_student_{s_id}",
                )
        except Exception:
            pass

        # Re-query ordered by rank for fresh ORM state
        return (
            db.query(Ranking)
            .options(joinedload(Ranking.student))
            .filter(Ranking.exam_id == exam_id)
            .order_by(Ranking.rank.asc())
            .all()
        )

    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to compute rankings: {str(exc)}",
        )


def get_leaderboard(
    exam_id: int,
    db: Session,
    current_user: User,
) -> LeaderboardResponse:
    """
    Retrieve full leaderboard for an examination.

    Authorization:
      - Admin: Any exam.
      - Examiner: Exams created by this examiner.
      - Student: Forbidden (403). Must use /my-rank instead.
    """
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Exam {exam_id} not found",
        )

    # Authorization checks
    if _is_student(current_user) and not _is_admin(current_user) and not _is_examiner(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Students are not authorized to view the full leaderboard. Use /exams/{exam_id}/my-rank to view your rank.",
        )

    if _is_examiner(current_user) and not _is_admin(current_user):
        if exam.created_by != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Examiners can only view leaderboards for exams they created",
            )

    # Load rankings
    rankings: List[Ranking] = (
        db.query(Ranking)
        .options(joinedload(Ranking.student))
        .filter(Ranking.exam_id == exam_id)
        .order_by(Ranking.rank.asc())
        .all()
    )

    # If no rankings are persisted yet, compute on the fly
    if not rankings:
        rankings = compute_rankings_for_exam(exam_id=exam_id, db=db)

    # Load Result rows map for percentage and submitted_at
    results_map: Dict[int, Tuple[float, datetime]] = {}
    record_pairs = (
        db.query(Result, ExamAttempt)
        .join(ExamAttempt, Result.attempt_id == ExamAttempt.id)
        .filter(ExamAttempt.exam_id == exam_id)
        .all()
    )
    for res, att in record_pairs:
        results_map[att.student_id] = (float(res.percentage), att.submitted_at)

    items: List[RankingItemResponse] = []
    for r in rankings:
        student = r.student or db.query(User).filter(User.id == r.student_id).first()
        res_info = results_map.get(r.student_id)
        percentage_val = res_info[0] if res_info else None
        submitted_at_val = res_info[1] if res_info else None

        items.append(RankingItemResponse(
            rank=r.rank,
            student_id=r.student_id,
            student_name=student.full_name if student else None,
            student_email=student.email if student else None,
            score=float(r.score),
            percentage=percentage_val,
            tie_break_time=format_duration(r.tie_break_time),
            submitted_at=submitted_at_val,
        ))

    return LeaderboardResponse(
        exam_id=exam_id,
        exam_title=exam.title,
        total_candidates=len(items),
        rankings=items,
    )


def get_my_rank(
    exam_id: int,
    db: Session,
    current_user: User,
) -> MyRankResponse:
    """
    Retrieve the current student's individual rank, score, and percentile standing.
    """
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Exam {exam_id} not found",
        )

    # Look up ranking
    ranking = (
        db.query(Ranking)
        .filter(Ranking.exam_id == exam_id, Ranking.student_id == current_user.id)
        .first()
    )

    if not ranking:
        # Check if attempt is finalized; compute if needed
        attempt = (
            db.query(ExamAttempt)
            .filter(
                ExamAttempt.exam_id == exam_id,
                ExamAttempt.student_id == current_user.id,
                ExamAttempt.status.in_(["submitted", "auto_submitted"]),
            )
            .first()
        )
        if attempt:
            compute_rankings_for_exam(exam_id=exam_id, db=db)
            ranking = (
                db.query(Ranking)
                .filter(Ranking.exam_id == exam_id, Ranking.student_id == current_user.id)
                .first()
            )

    if not ranking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rank not found. You must complete and submit the examination first.",
        )

    total_candidates = db.query(Ranking).filter(Ranking.exam_id == exam_id).count()

    # Percentile formula: ((total - rank + 1) / total) * 100
    if total_candidates > 0:
        percentile = round(((total_candidates - ranking.rank + 1) / total_candidates) * 100.0, 1)
    else:
        percentile = 100.0

    # Get percentage and submitted_at from Result/ExamAttempt
    res_record = (
        db.query(Result, ExamAttempt)
        .join(ExamAttempt, Result.attempt_id == ExamAttempt.id)
        .filter(ExamAttempt.exam_id == exam_id, ExamAttempt.student_id == current_user.id)
        .first()
    )
    percentage = float(res_record[0].percentage) if res_record else None
    submitted_at = res_record[1].submitted_at if res_record else None

    return MyRankResponse(
        exam_id=exam_id,
        exam_title=exam.title,
        student_id=current_user.id,
        student_name=current_user.full_name,
        rank=ranking.rank,
        score=float(ranking.score),
        percentage=percentage,
        total_candidates=total_candidates,
        percentile=percentile,
        tie_break_time=format_duration(ranking.tie_break_time),
        submitted_at=submitted_at,
    )
