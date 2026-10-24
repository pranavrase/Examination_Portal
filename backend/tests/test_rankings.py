"""
test_rankings.py — Module 2.11: Ranking Engine Tests
=====================================================
Tests verify:
  1. Empty exam produces empty leaderboard.
  2. Single student is assigned Rank 1.
  3. Multiple students with distinct scores are ranked in descending order.
  4. Tie-breaking: identical scores broken by earlier submission time.
  5. Deterministic tie-breaking: identical scores & submission times broken by student ID.
  6. Idempotency: recomputing rankings does not create duplicate rows.
  7. Student authorization: students cannot access full /leaderboard (403).
  8. Student self-rank: students can view own rank, score & percentile on /my-rank.
  9. Student without submission receives 404 on /my-rank.
 10. Examiner access: examiner can access full leaderboard for own exam.
 11. Examiner forbidden from other examiner's exam leaderboard (403).
 12. Admin access: admin can access leaderboard for any exam.
 13. Nonexistent exam returns 404.
 14. Data consistency: Ranking.score matches Result.total_marks_obtained.
 15. Incomplete / in_progress attempts excluded from rankings.
 16. Recalculate endpoint: POST /exams/{exam_id}/rankings/compute works for Admin/Examiner.
 17. Student forbidden from recalculate endpoint (403).
 18. Result calculation automatically triggers ranking updates.
"""

from typing import Tuple
import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal

from app.models.user import User
from app.models.role import Role
from app.models.exam import Exam, ExamSettings, ExamAssignment
from app.models.question import QuestionCategory, Question, McqOption, ExamQuestion
from app.models.attempt import ExamAttempt, AttemptAnswer
from app.models.result import Result, Ranking
from app.core.security import hash_password, create_access_token
from app.services.role_service import seed_default_roles
from app.services.ranking_service import (
    compute_rankings_for_exam,
    get_leaderboard,
    get_my_rank,
)
from app.services.result_service import calculate_final_score


def utc_now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def get_auth_header(user_id: int, email: str, role: str) -> dict:
    token = create_access_token(user_id=user_id, email=email, role=role)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def setup_rankings_fixtures(db_session):
    """Seed roles, users, and base exams for ranking tests."""
    seed_default_roles(db_session)

    student_role = db_session.query(Role).filter(Role.name == "student").first()
    examiner_role = db_session.query(Role).filter(Role.name == "examiner").first()
    admin_role = db_session.query(Role).filter(Role.name == "admin").first()

    admin = User(email="admin_rk@test.com", full_name="Admin User", password_hash=hash_password("x"), is_active=True)
    if admin_role:
        admin.roles.append(admin_role)
    db_session.add(admin)

    examiner1 = User(email="examiner1_rk@test.com", full_name="Examiner One", password_hash=hash_password("x"), is_active=True)
    if examiner_role:
        examiner1.roles.append(examiner_role)
    db_session.add(examiner1)

    examiner2 = User(email="examiner2_rk@test.com", full_name="Examiner Two", password_hash=hash_password("x"), is_active=True)
    if examiner_role:
        examiner2.roles.append(examiner_role)
    db_session.add(examiner2)

    s1 = User(email="s1_rk@test.com", full_name="Student One", password_hash=hash_password("x"), is_active=True)
    s2 = User(email="s2_rk@test.com", full_name="Student Two", password_hash=hash_password("x"), is_active=True)
    s3 = User(email="s3_rk@test.com", full_name="Student Three", password_hash=hash_password("x"), is_active=True)
    for s in [s1, s2, s3]:
        if student_role:
            s.roles.append(student_role)
        db_session.add(s)

    db_session.flush()

    # Create Exam 1 owned by examiner1
    exam1 = Exam(title="Rank Exam 1", created_by=examiner1.id, status="published")
    db_session.add(exam1)
    db_session.flush()
    db_session.add(ExamSettings(
        exam_id=exam1.id,
        duration_minutes=60,
        total_marks=100.0,
        passing_percentage=40.0,
        negative_marking_ratio=0.0,
    ))

    # Create Exam 2 owned by examiner2
    exam2 = Exam(title="Rank Exam 2", created_by=examiner2.id, status="published")
    db_session.add(exam2)
    db_session.flush()
    db_session.add(ExamSettings(
        exam_id=exam2.id,
        duration_minutes=45,
        total_marks=50.0,
        passing_percentage=50.0,
        negative_marking_ratio=0.0,
    ))

    # Question for Exam 1
    cat = QuestionCategory(name="General", topic="Rankings", difficulty="medium")
    db_session.add(cat)
    db_session.flush()
    q = Question(category_id=cat.id, question_type="mcq", question_text="Q1", marks=100.0, created_by=examiner1.id)
    db_session.add(q)
    db_session.flush()
    opt = McqOption(question_id=q.id, option_text="Correct", is_correct=True)
    db_session.add(opt)
    db_session.add(ExamQuestion(exam_id=exam1.id, question_id=q.id, question_order=1))

    # Assign students to Exam 1
    for s in [s1, s2, s3]:
        db_session.add(ExamAssignment(exam_id=exam1.id, student_id=s.id, assigned_at=utc_now()))

    db_session.commit()


def _create_submitted_attempt_with_result(
    db_session,
    exam_id: int,
    student_id: int,
    score: float,
    percentage: float = None,
    submitted_at: datetime = None,
    duration_minutes: int = 30,
) -> Tuple[ExamAttempt, Result]:
    """Helper to persist a finalized attempt and corresponding Result."""
    now = utc_now()
    sub_time = submitted_at or now
    start_time = sub_time - timedelta(minutes=duration_minutes)

    att = ExamAttempt(
        exam_id=exam_id,
        student_id=student_id,
        status="submitted",
        started_at=start_time,
        submitted_at=sub_time,
        created_at=start_time,
        updated_at=sub_time,
    )
    db_session.add(att)
    db_session.flush()

    pct = percentage if percentage is not None else score
    res = Result(
        attempt_id=att.id,
        total_marks_obtained=Decimal(str(score)),
        total_marks_possible=Decimal("100.0"),
        percentage=Decimal(str(pct)),
        pass_fail=score >= 40.0,
        calculated_at=sub_time,
    )
    db_session.add(res)
    db_session.commit()
    db_session.refresh(att)
    db_session.refresh(res)
    return att, res


# ─────────────────────────────────────────────────────────────────────────────
# Unit & Service Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_01_empty_exam_returns_empty_leaderboard(db_session):
    """An exam with no candidate results produces an empty leaderboard with count 0."""
    exam1 = db_session.query(Exam).filter(Exam.title == "Rank Exam 1").first()
    rankings = compute_rankings_for_exam(exam_id=exam1.id, db=db_session)
    assert rankings == []

    admin = db_session.query(User).filter(User.email == "admin_rk@test.com").first()
    lb = get_leaderboard(exam_id=exam1.id, db=db_session, current_user=admin)
    assert lb.total_candidates == 0
    assert lb.rankings == []


def test_02_single_student_ranking(db_session):
    """A single submitted student receives Rank 1."""
    exam1 = db_session.query(Exam).filter(Exam.title == "Rank Exam 1").first()
    s1 = db_session.query(User).filter(User.email == "s1_rk@test.com").first()

    _create_submitted_attempt_with_result(db_session, exam1.id, s1.id, score=90.0)

    rankings = compute_rankings_for_exam(exam_id=exam1.id, db=db_session)
    assert len(rankings) == 1
    assert rankings[0].student_id == s1.id
    assert rankings[0].rank == 1
    assert float(rankings[0].score) == 90.0


def test_03_multiple_students_different_scores(db_session):
    """Candidates with different scores are ranked: highest score first."""
    exam1 = db_session.query(Exam).filter(Exam.title == "Rank Exam 1").first()
    s1 = db_session.query(User).filter(User.email == "s1_rk@test.com").first()
    s2 = db_session.query(User).filter(User.email == "s2_rk@test.com").first()
    s3 = db_session.query(User).filter(User.email == "s3_rk@test.com").first()

    _create_submitted_attempt_with_result(db_session, exam1.id, s1.id, score=80.0)
    _create_submitted_attempt_with_result(db_session, exam1.id, s2.id, score=95.0)
    _create_submitted_attempt_with_result(db_session, exam1.id, s3.id, score=90.0)

    rankings = compute_rankings_for_exam(exam_id=exam1.id, db=db_session)
    assert len(rankings) == 3

    # Expected order: s2 (95) -> Rank 1, s3 (90) -> Rank 2, s1 (80) -> Rank 3
    assert rankings[0].student_id == s2.id
    assert rankings[0].rank == 1
    assert float(rankings[0].score) == 95.0

    assert rankings[1].student_id == s3.id
    assert rankings[1].rank == 2
    assert float(rankings[1].score) == 90.0

    assert rankings[2].student_id == s1.id
    assert rankings[2].rank == 3
    assert float(rankings[2].score) == 80.0


def test_04_same_score_earlier_submission_ranks_first(db_session):
    """
    Tie-breaker: When two candidates have identical scores,
    the candidate who submitted earlier receives the better rank.
    """
    exam1 = db_session.query(Exam).filter(Exam.title == "Rank Exam 1").first()
    s1 = db_session.query(User).filter(User.email == "s1_rk@test.com").first()
    s2 = db_session.query(User).filter(User.email == "s2_rk@test.com").first()

    base_time = utc_now()
    sub_early = base_time - timedelta(minutes=20)
    sub_late = base_time - timedelta(minutes=5)

    _create_submitted_attempt_with_result(db_session, exam1.id, s1.id, score=95.0, submitted_at=sub_late)
    _create_submitted_attempt_with_result(db_session, exam1.id, s2.id, score=95.0, submitted_at=sub_early)

    rankings = compute_rankings_for_exam(exam_id=exam1.id, db=db_session)
    assert len(rankings) == 2

    # s2 submitted earlier -> Rank 1
    assert rankings[0].student_id == s2.id
    assert rankings[0].rank == 1
    assert float(rankings[0].score) == 95.0

    # s1 submitted later -> Rank 2
    assert rankings[1].student_id == s1.id
    assert rankings[1].rank == 2
    assert float(rankings[1].score) == 95.0


def test_05_same_score_and_timestamp_deterministic_student_id(db_session):
    """
    Deterministic resolution: If both score and submission timestamp are identical,
    ordering falls back to deterministic student ID ascending.
    """
    exam1 = db_session.query(Exam).filter(Exam.title == "Rank Exam 1").first()
    s1 = db_session.query(User).filter(User.email == "s1_rk@test.com").first()
    s2 = db_session.query(User).filter(User.email == "s2_rk@test.com").first()

    exact_time = utc_now()
    _create_submitted_attempt_with_result(db_session, exam1.id, s1.id, score=85.0, submitted_at=exact_time)
    _create_submitted_attempt_with_result(db_session, exam1.id, s2.id, score=85.0, submitted_at=exact_time)

    rankings = compute_rankings_for_exam(exam_id=exam1.id, db=db_session)
    assert len(rankings) == 2

    first_student_id = min(s1.id, s2.id)
    second_student_id = max(s1.id, s2.id)

    assert rankings[0].student_id == first_student_id
    assert rankings[0].rank == 1
    assert rankings[1].student_id == second_student_id
    assert rankings[1].rank == 2


def test_06_recompute_rankings_idempotent(db_session):
    """
    Running compute_rankings_for_exam multiple times updates rows
    and never creates duplicate Ranking records.
    """
    exam1 = db_session.query(Exam).filter(Exam.title == "Rank Exam 1").first()
    s1 = db_session.query(User).filter(User.email == "s1_rk@test.com").first()
    s2 = db_session.query(User).filter(User.email == "s2_rk@test.com").first()

    _create_submitted_attempt_with_result(db_session, exam1.id, s1.id, score=70.0)
    _create_submitted_attempt_with_result(db_session, exam1.id, s2.id, score=85.0)

    # First run
    compute_rankings_for_exam(exam_id=exam1.id, db=db_session)
    count1 = db_session.query(Ranking).filter(Ranking.exam_id == exam1.id).count()
    assert count1 == 2

    # Second run
    compute_rankings_for_exam(exam_id=exam1.id, db=db_session)
    count2 = db_session.query(Ranking).filter(Ranking.exam_id == exam1.id).count()
    assert count2 == 2

    # Third run
    compute_rankings_for_exam(exam_id=exam1.id, db=db_session)
    count3 = db_session.query(Ranking).filter(Ranking.exam_id == exam1.id).count()
    assert count3 == 2


def test_07_student_cannot_access_full_leaderboard(client, db_session):
    """Students are rejected with 403 Forbidden when calling GET /exams/{id}/leaderboard."""
    exam1 = db_session.query(Exam).filter(Exam.title == "Rank Exam 1").first()
    s1 = db_session.query(User).filter(User.email == "s1_rk@test.com").first()
    headers = get_auth_header(s1.id, s1.email, "student")

    res = client.get(f"/exams/{exam1.id}/leaderboard", headers=headers)
    assert res.status_code == 403
    assert "not authorized" in res.json()["detail"].lower()


def test_08_student_can_view_own_rank(client, db_session):
    """Students can access GET /exams/{id}/my-rank and view their rank, score, and percentile."""
    exam1 = db_session.query(Exam).filter(Exam.title == "Rank Exam 1").first()
    s1 = db_session.query(User).filter(User.email == "s1_rk@test.com").first()
    s2 = db_session.query(User).filter(User.email == "s2_rk@test.com").first()

    _create_submitted_attempt_with_result(db_session, exam1.id, s1.id, score=75.0)
    _create_submitted_attempt_with_result(db_session, exam1.id, s2.id, score=90.0)
    compute_rankings_for_exam(exam_id=exam1.id, db=db_session)

    headers = get_auth_header(s1.id, s1.email, "student")
    res = client.get(f"/exams/{exam1.id}/my-rank", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["student_id"] == s1.id
    assert data["rank"] == 2
    assert data["score"] == 75.0
    assert data["total_candidates"] == 2
    assert data["percentile"] is not None


def test_09_student_without_submission_gets_404_on_my_rank(client, db_session):
    """Students who have not submitted the exam receive 404 Not Found on /my-rank."""
    exam1 = db_session.query(Exam).filter(Exam.title == "Rank Exam 1").first()
    s3 = db_session.query(User).filter(User.email == "s3_rk@test.com").first()
    headers = get_auth_header(s3.id, s3.email, "student")

    res = client.get(f"/exams/{exam1.id}/my-rank", headers=headers)
    assert res.status_code == 404


def test_10_examiner_can_view_own_exam_leaderboard(client, db_session):
    """Examiners can view the complete leaderboard for exams they created."""
    exam1 = db_session.query(Exam).filter(Exam.title == "Rank Exam 1").first()
    examiner1 = db_session.query(User).filter(User.email == "examiner1_rk@test.com").first()
    s1 = db_session.query(User).filter(User.email == "s1_rk@test.com").first()

    _create_submitted_attempt_with_result(db_session, exam1.id, s1.id, score=88.0)
    compute_rankings_for_exam(exam_id=exam1.id, db=db_session)

    headers = get_auth_header(examiner1.id, examiner1.email, "examiner")
    res = client.get(f"/exams/{exam1.id}/leaderboard", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["exam_id"] == exam1.id
    assert data["total_candidates"] == 1
    assert data["rankings"][0]["student_id"] == s1.id


def test_11_examiner_cannot_view_other_examiner_exam_leaderboard(client, db_session):
    """Examiners are rejected (403) when attempting to view another examiner's leaderboard."""
    exam1 = db_session.query(Exam).filter(Exam.title == "Rank Exam 1").first()  # owned by examiner1
    examiner2 = db_session.query(User).filter(User.email == "examiner2_rk@test.com").first()

    headers = get_auth_header(examiner2.id, examiner2.email, "examiner")
    res = client.get(f"/exams/{exam1.id}/leaderboard", headers=headers)
    assert res.status_code == 403


def test_12_admin_can_view_any_exam_leaderboard(client, db_session):
    """Admin has system-wide access to view any exam's leaderboard."""
    exam1 = db_session.query(Exam).filter(Exam.title == "Rank Exam 1").first()
    admin = db_session.query(User).filter(User.email == "admin_rk@test.com").first()

    headers = get_auth_header(admin.id, admin.email, "admin")
    res = client.get(f"/exams/{exam1.id}/leaderboard", headers=headers)
    assert res.status_code == 200


def test_13_nonexistent_exam_returns_404(client, db_session):
    """Querying a nonexistent exam returns 404 Not Found."""
    admin = db_session.query(User).filter(User.email == "admin_rk@test.com").first()
    headers = get_auth_header(admin.id, admin.email, "admin")

    res = client.get("/exams/999999/leaderboard", headers=headers)
    assert res.status_code == 404

    s1 = db_session.query(User).filter(User.email == "s1_rk@test.com").first()
    s_headers = get_auth_header(s1.id, s1.email, "student")
    res_my_rank = client.get("/exams/999999/my-rank", headers=s_headers)
    assert res_my_rank.status_code == 404


def test_14_ranking_score_matches_result_score(db_session):
    """Ranking score comes directly from Result.total_marks_obtained."""
    exam1 = db_session.query(Exam).filter(Exam.title == "Rank Exam 1").first()
    s1 = db_session.query(User).filter(User.email == "s1_rk@test.com").first()

    att, res = _create_submitted_attempt_with_result(db_session, exam1.id, s1.id, score=83.5)
    rankings = compute_rankings_for_exam(exam_id=exam1.id, db=db_session)

    assert float(rankings[0].score) == float(res.total_marks_obtained) == 83.5


def test_15_excluded_attempts_not_ranked(db_session):
    """Attempts that are still in_progress or lack a Result record are excluded from rankings."""
    exam1 = db_session.query(Exam).filter(Exam.title == "Rank Exam 1").first()
    s1 = db_session.query(User).filter(User.email == "s1_rk@test.com").first()
    s2 = db_session.query(User).filter(User.email == "s2_rk@test.com").first()

    # s1 is submitted with Result
    _create_submitted_attempt_with_result(db_session, exam1.id, s1.id, score=92.0)

    # s2 is in_progress
    att_in_prog = ExamAttempt(
        exam_id=exam1.id,
        student_id=s2.id,
        status="in_progress",
        started_at=utc_now(),
    )
    db_session.add(att_in_prog)
    db_session.commit()

    rankings = compute_rankings_for_exam(exam_id=exam1.id, db=db_session)
    assert len(rankings) == 1
    assert rankings[0].student_id == s1.id


def test_16_recalculate_rankings_endpoint_admin_and_examiner(client, db_session):
    """Admin and Examiner can invoke POST /exams/{id}/rankings/compute."""
    exam1 = db_session.query(Exam).filter(Exam.title == "Rank Exam 1").first()
    examiner1 = db_session.query(User).filter(User.email == "examiner1_rk@test.com").first()
    s1 = db_session.query(User).filter(User.email == "s1_rk@test.com").first()

    _create_submitted_attempt_with_result(db_session, exam1.id, s1.id, score=80.0)

    headers = get_auth_header(examiner1.id, examiner1.email, "examiner")
    res = client.post(f"/exams/{exam1.id}/rankings/compute", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["total_ranked"] == 1


def test_17_student_forbidden_from_recalculate_endpoint(client, db_session):
    """Students cannot trigger ranking recalculation (403 Forbidden)."""
    exam1 = db_session.query(Exam).filter(Exam.title == "Rank Exam 1").first()
    s1 = db_session.query(User).filter(User.email == "s1_rk@test.com").first()
    headers = get_auth_header(s1.id, s1.email, "student")

    res = client.post(f"/exams/{exam1.id}/rankings/compute", headers=headers)
    assert res.status_code == 403


def test_18_result_calculation_automatically_updates_rankings(db_session):
    """
    When Module 2.10 calculates a final score,
    the ranking engine hook automatically computes/updates the Ranking row.
    """
    exam1 = db_session.query(Exam).filter(Exam.title == "Rank Exam 1").first()
    s1 = db_session.query(User).filter(User.email == "s1_rk@test.com").first()
    q = db_session.query(Question).filter(Question.question_text == "Q1").first()
    opt = db_session.query(McqOption).filter(McqOption.question_id == q.id).first()

    now = utc_now()
    att = ExamAttempt(
        exam_id=exam1.id,
        student_id=s1.id,
        status="submitted",
        started_at=now - timedelta(minutes=30),
        submitted_at=now,
    )
    db_session.add(att)
    db_session.flush()

    ans = AttemptAnswer(
        attempt_id=att.id,
        question_id=q.id,
        selected_option_id=opt.id,
    )
    db_session.add(ans)
    db_session.commit()

    # Trigger Module 2.10 calculation
    calculate_final_score(db=db_session, attempt_id=att.id)

    # Verify Ranking row was automatically generated
    ranking = db_session.query(Ranking).filter(Ranking.exam_id == exam1.id, Ranking.student_id == s1.id).first()
    assert ranking is not None
    assert ranking.rank == 1
    assert float(ranking.score) == 100.0
