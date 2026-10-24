"""
Module 2.12 — Reporting Service
================================
Provides read-only examination, student, question, and candidate performance analytics.

Core Principles:
  * Read-only: strictly does not mutate ExamAttempt, Result, Ranking, or Question records.
  * Single Source of Truth:
      - Finalized scores & pass/fail: Result model (Module 2.10)
      - Ranks: Ranking model (Module 2.11)
      - Submissions & Attempts: ExamAttempt model
      - Question responses: AttemptAnswer & CodingSubmission models
  * Security & RBAC:
      - Student: only access own performance reports.
      - Examiner: access reports for exams they created.
      - Admin: system-wide reporting access.
  * Zero-record safety: guards against division by zero and returns clean zero-state structures.
  * Query Performance: aggregates database-side using joins and SQL aggregations.
"""

import csv
import io
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional, Tuple, Dict, Any

from fastapi import HTTPException, status
from sqlalchemy import func, and_, or_
from sqlalchemy.orm import Session, joinedload

from app.models.exam import Exam, ExamSettings
from app.models.attempt import ExamAttempt, AttemptAnswer, CodingSubmission, ExecutionResult
from app.models.question import Question, QuestionCategory, ExamQuestion, CodingQuestion
from app.models.result import Result, Ranking
from app.models.user import User
from app.schemas.report import (
    ExamPerformanceReport,
    StudentPerformanceItem,
    StudentPerformanceReport,
    QuestionPerformanceItem,
    ExamQuestionsReport,
    CandidateWiseReportItem,
    CandidateWiseReportResponse,
    TopicWiseReportItem,
    TopicWiseReportResponse,
)


def _user_roles(user: User) -> set:
    roles = {r.name.lower() for r in user.roles} if user.roles else set()
    if user.role:
        roles.add(user.role.lower())
    return roles


def _is_admin(user: User) -> bool:
    return "admin" in _user_roles(user)


def _is_examiner(user: User) -> bool:
    return "examiner" in _user_roles(user)


def _is_student(user: User) -> bool:
    return "student" in _user_roles(user)


def _verify_exam_access(exam: Exam, user: User) -> None:
    if _is_admin(user):
        return
    if _is_examiner(user) and exam.created_by == user.id:
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You do not have permission to view reports for this examination.",
    )


def _parse_datetime(dt_val: Any) -> Optional[datetime]:
    if not dt_val:
        return None
    if isinstance(dt_val, datetime):
        return dt_val
    if isinstance(dt_val, str):
        try:
            return datetime.fromisoformat(dt_val.replace("Z", "+00:00")).replace(tzinfo=None)
        except (ValueError, TypeError):
            try:
                return datetime.strptime(dt_val, "%Y-%m-%d")
            except (ValueError, TypeError):
                return None
    return None


def get_exam_performance_report(
    exam_id: int,
    db: Session,
    current_user: User,
) -> ExamPerformanceReport:
    """
    Computes summary performance statistics for an exam.
    """
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Exam with ID {exam_id} not found.",
        )

    _verify_exam_access(exam, current_user)

    # Attempt counts
    total_attempts = (
        db.query(func.count(ExamAttempt.id))
        .filter(ExamAttempt.exam_id == exam_id)
        .scalar()
        or 0
    )

    total_students = (
        db.query(func.count(func.distinct(ExamAttempt.student_id)))
        .filter(ExamAttempt.exam_id == exam_id)
        .scalar()
        or 0
    )

    completed_attempts = (
        db.query(func.count(ExamAttempt.id))
        .filter(
            ExamAttempt.exam_id == exam_id,
            ExamAttempt.status.in_(["submitted", "auto_submitted"]),
        )
        .scalar()
        or 0
    )

    in_progress_attempts = (
        db.query(func.count(ExamAttempt.id))
        .filter(
            ExamAttempt.exam_id == exam_id,
            ExamAttempt.status == "in_progress",
        )
        .scalar()
        or 0
    )

    # Finalized Results aggregations
    result_base = (
        db.query(Result)
        .join(ExamAttempt, Result.attempt_id == ExamAttempt.id)
        .filter(
            ExamAttempt.exam_id == exam_id,
            ExamAttempt.status.in_(["submitted", "auto_submitted"]),
        )
    )

    passed_count = result_base.filter(Result.pass_fail.is_(True)).count()
    failed_count = result_base.filter(Result.pass_fail.is_(False)).count()

    stats = (
        db.query(
            func.avg(Result.total_marks_obtained),
            func.max(Result.total_marks_obtained),
            func.min(Result.total_marks_obtained),
            func.avg(Result.percentage),
        )
        .join(ExamAttempt, Result.attempt_id == ExamAttempt.id)
        .filter(
            ExamAttempt.exam_id == exam_id,
            ExamAttempt.status.in_(["submitted", "auto_submitted"]),
        )
        .first()
    )

    avg_score = round(float(stats[0]), 2) if stats and stats[0] is not None else 0.0
    max_score = round(float(stats[1]), 2) if stats and stats[1] is not None else 0.0
    min_score = round(float(stats[2]), 2) if stats and stats[2] is not None else 0.0
    avg_pct = round(float(stats[3]), 2) if stats and stats[3] is not None else 0.0

    return ExamPerformanceReport(
        exam_id=exam.id,
        exam_name=exam.title,
        exam_title=exam.title,
        total_attempts=total_attempts,
        total_students=total_students,
        completed_attempts=completed_attempts,
        in_progress_attempts=in_progress_attempts,
        passed_students=passed_count,
        passed_count=passed_count,
        failed_students=failed_count,
        failed_count=failed_count,
        average_score=avg_score,
        highest_score=max_score,
        lowest_score=min_score,
        average_percentage=avg_pct,
    )


def get_student_performance_report(
    student_id: int,
    db: Session,
    current_user: User,
) -> StudentPerformanceReport:
    """
    Retrieves performance report for a student across all completed exams.
    """
    student = db.query(User).filter(User.id == student_id).first()
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Student with ID {student_id} not found.",
        )

    # Authorization enforcement:
    # 1. Student can only view their own performance.
    # 2. Examiner can view if student took examiner's exam (scoped to examiner's exams).
    # 3. Admin has complete access.
    if _is_student(current_user) and current_user.id != student_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: you are not authorized to view another student's report.",
        )

    attempts_query = (
        db.query(ExamAttempt)
        .options(joinedload(ExamAttempt.exam), joinedload(ExamAttempt.result))
        .filter(
            ExamAttempt.student_id == student_id,
            ExamAttempt.status.in_(["submitted", "auto_submitted"]),
        )
    )

    if _is_examiner(current_user) and not _is_admin(current_user):
        attempts_query = attempts_query.join(Exam, ExamAttempt.exam_id == Exam.id).filter(
            Exam.created_by == current_user.id
        )

    attempts = attempts_query.order_by(ExamAttempt.submitted_at.desc()).all()

    exam_items: List[StudentPerformanceItem] = []
    total_pct_sum = Decimal("0.0")

    for att in attempts:
        res: Optional[Result] = att.result
        if not res:
            continue

        # Look up Ranking record for this exam & student
        ranking = (
            db.query(Ranking)
            .filter(Ranking.exam_id == att.exam_id, Ranking.student_id == student_id)
            .first()
        )
        rank_val = ranking.rank if ranking else None

        exam_title = att.exam.title if att.exam else f"Exam #{att.exam_id}"
        total_marks = float(res.total_marks_possible)
        marks_obtained = float(res.total_marks_obtained)
        pct = float(res.percentage)
        total_pct_sum += Decimal(str(pct))

        exam_items.append(
            StudentPerformanceItem(
                exam_id=att.exam_id,
                exam_name=exam_title,
                attempt_id=att.id,
                status=att.status,
                total_marks=total_marks,
                marks_obtained=marks_obtained,
                percentage=pct,
                pass_fail=res.pass_fail,
                rank=rank_val,
                submitted_at=att.submitted_at,
            )
        )

    total_exams = len(exam_items)
    passed_count = sum(1 for item in exam_items if item.pass_fail)
    failed_count = total_exams - passed_count
    avg_percentage = round(float(total_pct_sum / total_exams), 2) if total_exams > 0 else 0.0

    return StudentPerformanceReport(
        student_id=student.id,
        student_name=student.full_name or student.email,
        student_email=student.email,
        total_exams_taken=total_exams,
        passed_exams=passed_count,
        failed_exams=failed_count,
        average_percentage=avg_percentage,
        exams=exam_items,
    )


def get_my_performance_report(
    db: Session,
    current_user: User,
) -> StudentPerformanceReport:
    """
    Retrieves performance report for the currently authenticated student.
    """
    return get_student_performance_report(
        student_id=current_user.id,
        db=db,
        current_user=current_user,
    )


def get_exam_questions_report(
    exam_id: int,
    db: Session,
    current_user: User,
) -> ExamQuestionsReport:
    """
    Generates question-level accuracy and attempt breakdown for an examination.
    """
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Exam with ID {exam_id} not found.",
        )

    _verify_exam_access(exam, current_user)

    # Completed attempt IDs for this exam
    completed_attempt_rows = (
        db.query(ExamAttempt.id)
        .filter(
            ExamAttempt.exam_id == exam_id,
            ExamAttempt.status.in_(["submitted", "auto_submitted"]),
        )
        .all()
    )
    completed_attempt_ids = [r[0] for r in completed_attempt_rows]
    total_completed = len(completed_attempt_ids)

    # Questions linked to this exam
    exam_questions = (
        db.query(ExamQuestion)
        .options(
            joinedload(ExamQuestion.question).joinedload(Question.category),
            joinedload(ExamQuestion.question).joinedload(Question.coding_details),
        )
        .filter(ExamQuestion.exam_id == exam_id)
        .order_by(ExamQuestion.question_order.asc())
        .all()
    )

    items: List[QuestionPerformanceItem] = []

    for eq in exam_questions:
        q: Question = eq.question
        if not q:
            continue

        topic_name = q.category.topic or q.category.name if q.category else None

        if q.question_type == "mcq":
            if completed_attempt_ids:
                answers = (
                    db.query(AttemptAnswer)
                    .filter(
                        AttemptAnswer.attempt_id.in_(completed_attempt_ids),
                        AttemptAnswer.question_id == q.id,
                    )
                    .all()
                )
            else:
                answers = []

            # Only count attempts where student actually selected an answer or record exists
            answered = [a for a in answers if a.selected_option_id is not None or a.is_correct is not None]
            total_att = len(answered)
            correct_cnt = sum(1 for a in answered if a.is_correct is True)
            incorrect_cnt = sum(1 for a in answered if a.is_correct is False)
            unanswered_cnt = max(0, total_completed - total_att)
            accuracy = round((correct_cnt / total_att) * 100, 2) if total_att > 0 else 0.0

        elif q.question_type == "coding":
            # For coding questions, look at coding submissions for this attempt
            coding_q = q.coding_details
            if completed_attempt_ids and coding_q:
                submissions = (
                    db.query(CodingSubmission)
                    .filter(
                        CodingSubmission.attempt_id.in_(completed_attempt_ids),
                        CodingSubmission.coding_question_id == coding_q.id,
                    )
                    .all()
                )
            else:
                submissions = []

            # Group submissions by attempt_id, taking the final or best
            attempt_subs: Dict[int, CodingSubmission] = {}
            for s in submissions:
                if s.attempt_id not in attempt_subs or s.is_final:
                    attempt_subs[s.attempt_id] = s

            total_att = len(attempt_subs)
            correct_cnt = sum(1 for s in attempt_subs.values() if s.score and float(s.score) > 0)
            incorrect_cnt = sum(1 for s in attempt_subs.values() if not s.score or float(s.score) == 0)
            unanswered_cnt = max(0, total_completed - total_att)
            accuracy = round((correct_cnt / total_att) * 100, 2) if total_att > 0 else 0.0

        else:
            total_att = 0
            correct_cnt = 0
            incorrect_cnt = 0
            unanswered_cnt = total_completed
            accuracy = 0.0

        items.append(
            QuestionPerformanceItem(
                question_id=q.id,
                question_text=q.question_text,
                question_type=q.question_type,
                topic=topic_name,
                total_attempts=total_att,
                correct_count=correct_cnt,
                incorrect_count=incorrect_cnt,
                unanswered_count=unanswered_cnt,
                accuracy_percentage=accuracy,
            )
        )

    return ExamQuestionsReport(
        exam_id=exam.id,
        exam_title=exam.title,
        total_questions=len(items),
        questions=items,
    )


def get_candidate_wise_report(
    exam_id: Optional[int],
    topic: Optional[str],
    candidate: Optional[str],
    from_date: Optional[str],
    to_date: Optional[str],
    page: int,
    limit: int,
    db: Session,
    current_user: User,
) -> CandidateWiseReportResponse:
    """
    Returns candidate-wise exam results with filtering, search, and pagination.
    Used by the examiner dashboard and report exports.
    """
    if _is_student(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: students cannot access candidate-wise reports.",
        )

    # Base query: finalized ExamAttempt with Result, Exam, and User
    query = (
        db.query(Result, ExamAttempt, Exam, User, Ranking.rank)
        .join(ExamAttempt, Result.attempt_id == ExamAttempt.id)
        .join(Exam, ExamAttempt.exam_id == Exam.id)
        .join(User, ExamAttempt.student_id == User.id)
        .outerjoin(
            Ranking,
            and_(
                Ranking.exam_id == ExamAttempt.exam_id,
                Ranking.student_id == ExamAttempt.student_id,
            ),
        )
        .filter(ExamAttempt.status.in_(["submitted", "auto_submitted"]))
    )

    # Scoping: If examiner (and not admin), restrict to exams owned by examiner
    if _is_examiner(current_user) and not _is_admin(current_user):
        query = query.filter(Exam.created_by == current_user.id)

    # Filters
    if exam_id:
        query = query.filter(Exam.id == exam_id)

    if candidate and candidate.strip():
        search_term = f"%{candidate.strip()}%"
        query = query.filter(
            or_(
                User.full_name.ilike(search_term),
                User.email.ilike(search_term),
            )
        )

    from_dt = _parse_datetime(from_date)
    if from_dt:
        query = query.filter(ExamAttempt.submitted_at >= from_dt)

    to_dt = _parse_datetime(to_date)
    if to_dt:
        # Include entire end of day if only date given
        if to_dt.hour == 0 and to_dt.minute == 0:
            to_dt = to_dt.replace(hour=23, minute=59, second=59)
        query = query.filter(ExamAttempt.submitted_at <= to_dt)

    total = query.count()

    # Deterministic order
    records = (
        query.order_by(
            Ranking.rank.asc().nullslast(),
            Result.total_marks_obtained.desc(),
            ExamAttempt.submitted_at.desc(),
        )
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    candidate_items: List[CandidateWiseReportItem] = []
    for res, att, ex, usr, rnk in records:
        status_str = "passed" if res.pass_fail else "failed"
        score_val = float(res.total_marks_obtained)
        total_val = float(res.total_marks_possible)
        pct_val = float(res.percentage)

        candidate_items.append(
            CandidateWiseReportItem(
                rank=rnk,
                candidate_id=usr.id,
                student_id=usr.id,
                candidate_name=usr.full_name or usr.email,
                student_name=usr.full_name or usr.email,
                candidate_email=usr.email,
                exam_id=ex.id,
                exam_name=ex.title,
                score=score_val,
                marks_obtained=score_val,
                total_marks=total_val,
                percentage=pct_val,
                status=status_str,
                pass_fail_status=status_str,
                attempt_date=att.submitted_at,
            )
        )

    return CandidateWiseReportResponse(
        total=total,
        page=page,
        limit=limit,
        candidates=candidate_items,
    )


def get_topic_wise_report(
    exam_id: Optional[int],
    topic: Optional[str],
    from_date: Optional[str],
    to_date: Optional[str],
    db: Session,
    current_user: User,
) -> TopicWiseReportResponse:
    """
    Aggregates performance across question categories/topics.
    """
    if _is_student(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: students cannot access topic-wise reports.",
        )

    # Base query for questions in scope
    eq_query = (
        db.query(ExamQuestion, Question, QuestionCategory, Exam)
        .join(Question, ExamQuestion.question_id == Question.id)
        .join(Exam, ExamQuestion.exam_id == Exam.id)
        .outerjoin(QuestionCategory, Question.category_id == QuestionCategory.id)
    )

    if _is_examiner(current_user) and not _is_admin(current_user):
        eq_query = eq_query.filter(Exam.created_by == current_user.id)

    if exam_id:
        eq_query = eq_query.filter(Exam.id == exam_id)

    if topic and topic.strip():
        eq_query = eq_query.filter(
            or_(
                QuestionCategory.topic.ilike(f"%{topic.strip()}%"),
                QuestionCategory.name.ilike(f"%{topic.strip()}%"),
            )
        )

    exam_questions = eq_query.all()

    # Group exam questions by topic name
    topics_map: Dict[str, Dict[str, Any]] = {}
    for eq, q, cat, ex in exam_questions:
        t_name = cat.topic if cat and cat.topic else (cat.name if cat and cat.name else "General")
        if t_name not in topics_map:
            topics_map[t_name] = {
                "question_ids": set(),
                "exam_ids": set(),
            }
        topics_map[t_name]["question_ids"].add(q.id)
        topics_map[t_name]["exam_ids"].add(ex.id)

    # For each topic, aggregate attempts and accuracy
    from_dt = _parse_datetime(from_date)
    to_dt = _parse_datetime(to_date)
    if to_dt and to_dt.hour == 0 and to_dt.minute == 0:
        to_dt = to_dt.replace(hour=23, minute=59, second=59)

    topic_items: List[TopicWiseReportItem] = []

    for t_name, data in topics_map.items():
        q_ids = list(data["question_ids"])
        e_ids = list(data["exam_ids"])

        # Completed attempts in scope
        att_query = db.query(ExamAttempt).filter(
            ExamAttempt.exam_id.in_(e_ids),
            ExamAttempt.status.in_(["submitted", "auto_submitted"]),
        )
        if from_dt:
            att_query = att_query.filter(ExamAttempt.submitted_at >= from_dt)
        if to_dt:
            att_query = att_query.filter(ExamAttempt.submitted_at <= to_dt)

        completed_attempts = att_query.all()
        att_ids = [a.id for a in completed_attempts]
        total_candidates = len({a.student_id for a in completed_attempts})

        if not att_ids:
            topic_items.append(
                TopicWiseReportItem(
                    topic=t_name,
                    candidates_attempted=0,
                    questions_count=len(q_ids),
                    avg_score=0.0,
                    average_score=0.0,
                    max_score=0.0,
                    min_score=0.0,
                    accuracy=0.0,
                    correct_answers=0,
                    incorrect_answers=0,
                    unanswered_questions=0,
                )
            )
            continue

        # Answers for these questions
        answers = (
            db.query(AttemptAnswer)
            .filter(
                AttemptAnswer.attempt_id.in_(att_ids),
                AttemptAnswer.question_id.in_(q_ids),
            )
            .all()
        )

        valid_answers = [a for a in answers if a.is_correct is not None]
        correct_cnt = sum(1 for a in valid_answers if a.is_correct is True)
        incorrect_cnt = sum(1 for a in valid_answers if a.is_correct is False)
        answered_total = len(valid_answers)

        total_possible_answers = len(att_ids) * len(q_ids)
        unanswered_cnt = max(0, total_possible_answers - answered_total)

        accuracy = round((correct_cnt / answered_total) * 100, 1) if answered_total > 0 else 0.0

        scores = [float(a.marks_awarded) for a in answers if a.marks_awarded is not None]
        avg_score = round(sum(scores) / len(scores), 1) if scores else 0.0
        max_score = round(max(scores), 1) if scores else 0.0
        min_score = round(min(scores), 1) if scores else 0.0

        topic_items.append(
            TopicWiseReportItem(
                topic=t_name,
                candidates_attempted=total_candidates,
                questions_count=len(q_ids),
                avg_score=avg_score,
                average_score=avg_score,
                max_score=max_score,
                min_score=min_score,
                accuracy=accuracy,
                correct_answers=correct_cnt,
                incorrect_answers=incorrect_cnt,
                unanswered_questions=unanswered_cnt,
            )
        )

    topic_items.sort(key=lambda x: x.topic)
    return TopicWiseReportResponse(topics=topic_items)


def export_report_csv(
    exam_id: Optional[int],
    topic: Optional[str],
    candidate: Optional[str],
    from_date: Optional[str],
    to_date: Optional[str],
    db: Session,
    current_user: User,
) -> str:
    """
    Generates a CSV string of candidate performance results for download.
    """
    report = get_candidate_wise_report(
        exam_id=exam_id,
        topic=topic,
        candidate=candidate,
        from_date=from_date,
        to_date=to_date,
        page=1,
        limit=10000,
        db=db,
        current_user=current_user,
    )

    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow([
        "Rank",
        "Candidate ID",
        "Candidate Name",
        "Email",
        "Exam ID",
        "Exam Name",
        "Score",
        "Total Marks",
        "Percentage",
        "Status",
        "Attempt Date",
    ])

    for item in report.candidates:
        writer.writerow([
            item.rank if item.rank is not None else "N/A",
            item.candidate_id,
            item.candidate_name,
            item.candidate_email or "",
            item.exam_id,
            item.exam_name,
            item.score,
            item.total_marks,
            item.percentage,
            item.status,
            item.attempt_date.strftime("%Y-%m-%d %H:%M:%S") if item.attempt_date else "N/A",
        ])

    return output.getvalue()
