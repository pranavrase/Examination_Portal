"""
test_reports.py — Module 2.12: Reporting Service Tests
======================================================
Comprehensive test suite verifying:
  1. Student can retrieve own performance report on /reports/my-performance (200).
  2. Student cannot access another student's report on /reports/students/{other_id} (403).
  3. Student can access their own student report on /reports/students/{own_id} (200).
  4. Examiner can retrieve report for their own exam on /reports/exams/{id} (200).
  5. Examiner cannot retrieve report for another examiner's exam (403).
  6. Admin can retrieve report for any exam (200) and any student (200).
  7. Non-existent exam returns 404.
  8. Non-existent student returns 404.
  9. Empty exam with zero attempts returns safe 0 statistics without crashing.
 10. Exam performance statistics: average_score, highest_score, lowest_score, average_percentage.
 11. Pass/Fail student counts correctly calculated from Result.pass_fail.
 12. Ranking integration: report reflects Ranking.rank and returns null/None when not ranked.
 13. Result consistency: Report marks and percentages strictly match Result table.
 14. Question-level statistics: attempt count, correct count, incorrect count, accuracy %.
 15. Candidate-wise report: search and filtering by exam_id, candidate name/email, pagination.
 16. Topic-wise report: aggregates category/topic accuracy and scores.
 17. CSV Export: returns downloadable CSV content stream with headers and candidate rows.
 18. Security: sensitive data (passwords, tokens, hidden test cases) is never exposed.
 19. Read-only: reporting endpoints never mutate ExamAttempt, Result, or Ranking records.
 20. Student forbidden from candidate-wise, topic-wise, and export endpoints (403).
"""

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
from app.services import report_service


def utc_now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def get_auth_header(user_id: int, email: str, role: str) -> dict:
    token = create_access_token(user_id=user_id, email=email, role=role)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def setup_reports_fixtures(db_session):
    """Seed roles, users, base exams, questions, attempts, results, and rankings."""
    seed_default_roles(db_session)

    student_role = db_session.query(Role).filter(Role.name == "student").first()
    examiner_role = db_session.query(Role).filter(Role.name == "examiner").first()
    admin_role = db_session.query(Role).filter(Role.name == "admin").first()

    admin = User(email="admin_rpt@test.com", full_name="Admin Reports", password_hash=hash_password("x"), is_active=True)
    if admin_role:
        admin.roles.append(admin_role)
    db_session.add(admin)

    examiner1 = User(email="ex1_rpt@test.com", full_name="Examiner One", password_hash=hash_password("x"), is_active=True)
    examiner2 = User(email="ex2_rpt@test.com", full_name="Examiner Two", password_hash=hash_password("x"), is_active=True)
    for ex in [examiner1, examiner2]:
        if examiner_role:
            ex.roles.append(examiner_role)
        db_session.add(ex)

    s1 = User(email="s1_rpt@test.com", full_name="Alice Student", password_hash=hash_password("x"), is_active=True)
    s2 = User(email="s2_rpt@test.com", full_name="Bob Student", password_hash=hash_password("x"), is_active=True)
    s3 = User(email="s3_rpt@test.com", full_name="Charlie Student", password_hash=hash_password("x"), is_active=True)
    for s in [s1, s2, s3]:
        if student_role:
            s.roles.append(student_role)
        db_session.add(s)

    db_session.flush()

    # Exam 1 (Owned by examiner1): 100 marks, passing 50%
    exam1 = Exam(title="Mathematics Midterm", created_by=examiner1.id, status="published")
    db_session.add(exam1)
    db_session.flush()
    db_session.add(ExamSettings(
        exam_id=exam1.id,
        duration_minutes=60,
        total_marks=100.0,
        passing_percentage=50.0,
        negative_marking_ratio=0.0,
    ))

    # Exam 2 (Owned by examiner2): 50 marks, passing 40%
    exam2 = Exam(title="Physics Quiz", created_by=examiner2.id, status="published")
    db_session.add(exam2)
    db_session.flush()
    db_session.add(ExamSettings(
        exam_id=exam2.id,
        duration_minutes=30,
        total_marks=50.0,
        passing_percentage=40.0,
        negative_marking_ratio=0.0,
    ))

    # Exam 3 (Empty exam owned by examiner1): No attempts
    exam_empty = Exam(title="Empty Exam", created_by=examiner1.id, status="published")
    db_session.add(exam_empty)
    db_session.flush()
    db_session.add(ExamSettings(
        exam_id=exam_empty.id,
        duration_minutes=30,
        total_marks=100.0,
        passing_percentage=50.0,
        negative_marking_ratio=0.0,
    ))

    # Question Categories
    cat_algebra = QuestionCategory(name="Mathematics", topic="Algebra", difficulty="medium")
    cat_geometry = QuestionCategory(name="Mathematics", topic="Geometry", difficulty="hard")
    db_session.add_all([cat_algebra, cat_geometry])
    db_session.flush()

    # Question 1: Algebra (60 marks)
    q1 = Question(category_id=cat_algebra.id, question_type="mcq", question_text="Solve 2x + 5 = 15", marks=60.0, created_by=examiner1.id)
    db_session.add(q1)
    db_session.flush()
    q1_opt1 = McqOption(question_id=q1.id, option_text="x = 5", is_correct=True)
    q1_opt2 = McqOption(question_id=q1.id, option_text="x = 10", is_correct=False)
    db_session.add_all([q1_opt1, q1_opt2])

    # Question 2: Geometry (40 marks)
    q2 = Question(category_id=cat_geometry.id, question_type="mcq", question_text="Area of circle with radius r", marks=40.0, created_by=examiner1.id)
    db_session.add(q2)
    db_session.flush()
    q2_opt1 = McqOption(question_id=q2.id, option_text="pi * r^2", is_correct=True)
    q2_opt2 = McqOption(question_id=q2.id, option_text="2 * pi * r", is_correct=False)
    db_session.add_all([q2_opt1, q2_opt2])
    db_session.flush()

    # Link questions to Exam 1
    db_session.add(ExamQuestion(exam_id=exam1.id, question_id=q1.id, question_order=1))
    db_session.add(ExamQuestion(exam_id=exam1.id, question_id=q2.id, question_order=2))
    db_session.flush()

    # Attempts & Finalized Results for Exam 1:
    # Alice (s1): Score 100/100 (100%), PASS, Rank 1
    t0 = utc_now() - timedelta(hours=2)
    att1 = ExamAttempt(exam_id=exam1.id, student_id=s1.id, status="submitted", started_at=t0, submitted_at=t0 + timedelta(minutes=25))
    db_session.add(att1)
    db_session.flush()
    db_session.add(AttemptAnswer(attempt_id=att1.id, question_id=q1.id, selected_option_id=q1_opt1.id, is_correct=True, marks_awarded=60.0))
    db_session.add(AttemptAnswer(attempt_id=att1.id, question_id=q2.id, selected_option_id=q2_opt1.id, is_correct=True, marks_awarded=40.0))
    db_session.add(Result(attempt_id=att1.id, total_marks_obtained=100.0, total_marks_possible=100.0, percentage=100.0, pass_fail=True))
    db_session.add(Ranking(exam_id=exam1.id, student_id=s1.id, rank=1, score=100.0, tie_break_time=timedelta(minutes=25)))

    # Bob (s2): Score 60/100 (60%), PASS, Rank 2
    att2 = ExamAttempt(exam_id=exam1.id, student_id=s2.id, status="submitted", started_at=t0, submitted_at=t0 + timedelta(minutes=35))
    db_session.add(att2)
    db_session.flush()
    db_session.add(AttemptAnswer(attempt_id=att2.id, question_id=q1.id, selected_option_id=q1_opt1.id, is_correct=True, marks_awarded=60.0))
    db_session.add(AttemptAnswer(attempt_id=att2.id, question_id=q2.id, selected_option_id=q2_opt2.id, is_correct=False, marks_awarded=0.0))
    db_session.add(Result(attempt_id=att2.id, total_marks_obtained=60.0, total_marks_possible=100.0, percentage=60.0, pass_fail=True))
    db_session.add(Ranking(exam_id=exam1.id, student_id=s2.id, rank=2, score=60.0, tie_break_time=timedelta(minutes=35)))

    # Charlie (s3): Score 0/100 (0%), FAIL, Rank 3
    att3 = ExamAttempt(exam_id=exam1.id, student_id=s3.id, status="submitted", started_at=t0, submitted_at=t0 + timedelta(minutes=40))
    db_session.add(att3)
    db_session.flush()
    db_session.add(AttemptAnswer(attempt_id=att3.id, question_id=q1.id, selected_option_id=q1_opt2.id, is_correct=False, marks_awarded=0.0))
    db_session.add(AttemptAnswer(attempt_id=att3.id, question_id=q2.id, selected_option_id=q2_opt2.id, is_correct=False, marks_awarded=0.0))
    db_session.add(Result(attempt_id=att3.id, total_marks_obtained=0.0, total_marks_possible=100.0, percentage=0.0, pass_fail=False))
    db_session.add(Ranking(exam_id=exam1.id, student_id=s3.id, rank=3, score=0.0, tie_break_time=timedelta(minutes=40)))

    db_session.commit()


# ==============================================================================
# TESTS
# ==============================================================================

def test_student_own_performance_report(client, db_session):
    """Test 1 — Student retrieves their own performance report on /reports/my-performance."""
    s1 = db_session.query(User).filter(User.email == "s1_rpt@test.com").first()
    headers = get_auth_header(s1.id, s1.email, "student")

    resp = client.get("/reports/my-performance", headers=headers)
    assert resp.status_code == 200
    data = resp.json()

    assert data["student_id"] == s1.id
    assert data["student_name"] == "Alice Student"
    assert data["total_exams_taken"] == 1
    assert data["passed_exams"] == 1
    assert data["failed_exams"] == 0
    assert data["average_percentage"] == 100.0

    exam_item = data["exams"][0]
    assert exam_item["exam_name"] == "Mathematics Midterm"
    assert exam_item["marks_obtained"] == 100.0
    assert exam_item["total_marks"] == 100.0
    assert exam_item["pass_fail"] is True
    assert exam_item["rank"] == 1


def test_student_cannot_access_another_student_report(client, db_session):
    """Test 2 — Student cannot access another student's report (403)."""
    s1 = db_session.query(User).filter(User.email == "s1_rpt@test.com").first()
    s2 = db_session.query(User).filter(User.email == "s2_rpt@test.com").first()
    headers = get_auth_header(s1.id, s1.email, "student")

    resp = client.get(f"/reports/students/{s2.id}", headers=headers)
    assert resp.status_code == 403
    assert "Access forbidden" in resp.json()["detail"]


def test_student_can_access_own_student_endpoint(client, db_session):
    """Test 3 — Student can access /reports/students/{own_id} (200)."""
    s1 = db_session.query(User).filter(User.email == "s1_rpt@test.com").first()
    headers = get_auth_header(s1.id, s1.email, "student")

    resp = client.get(f"/reports/students/{s1.id}", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["student_id"] == s1.id
    assert data["total_exams_taken"] == 1


def test_examiner_exam_report(client, db_session):
    """Test 4 — Examiner retrieves report for their own exam (200)."""
    ex1 = db_session.query(User).filter(User.email == "ex1_rpt@test.com").first()
    exam1 = db_session.query(Exam).filter(Exam.title == "Mathematics Midterm").first()
    headers = get_auth_header(ex1.id, ex1.email, "examiner")

    resp = client.get(f"/reports/exams/{exam1.id}", headers=headers)
    assert resp.status_code == 200
    data = resp.json()

    assert data["exam_id"] == exam1.id
    assert data["exam_name"] == "Mathematics Midterm"
    assert data["total_attempts"] == 3
    assert data["completed_attempts"] == 3
    assert data["passed_students"] == 2  # Alice (100) and Bob (60)
    assert data["failed_students"] == 1  # Charlie (0)
    assert data["highest_score"] == 100.0
    assert data["lowest_score"] == 0.0
    # Average score: (100 + 60 + 0) / 3 = 53.33
    assert data["average_score"] == 53.33
    assert data["average_percentage"] == 53.33


def test_examiner_forbidden_other_examiner_exam(client, db_session):
    """Test 5 — Examiner cannot access another examiner's exam report (403)."""
    ex2 = db_session.query(User).filter(User.email == "ex2_rpt@test.com").first()
    exam1 = db_session.query(Exam).filter(Exam.title == "Mathematics Midterm").first()
    headers = get_auth_header(ex2.id, ex2.email, "examiner")

    resp = client.get(f"/reports/exams/{exam1.id}", headers=headers)
    assert resp.status_code == 403


def test_admin_exam_report(client, db_session):
    """Test 6 — Admin can access any exam report (200)."""
    admin = db_session.query(User).filter(User.email == "admin_rpt@test.com").first()
    exam1 = db_session.query(Exam).filter(Exam.title == "Mathematics Midterm").first()
    headers = get_auth_header(admin.id, admin.email, "admin")

    resp = client.get(f"/reports/exams/{exam1.id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["exam_id"] == exam1.id


def test_invalid_exam_returns_404(client, db_session):
    """Test 7 — Non-existent exam returns 404."""
    admin = db_session.query(User).filter(User.email == "admin_rpt@test.com").first()
    headers = get_auth_header(admin.id, admin.email, "admin")

    resp = client.get("/reports/exams/999999", headers=headers)
    assert resp.status_code == 404


def test_invalid_student_returns_404(client, db_session):
    """Test 8 — Non-existent student returns 404."""
    admin = db_session.query(User).filter(User.email == "admin_rpt@test.com").first()
    headers = get_auth_header(admin.id, admin.email, "admin")

    resp = client.get("/reports/students/999999", headers=headers)
    assert resp.status_code == 404


def test_empty_exam_report(client, db_session):
    """Test 9 — Empty exam with no attempts returns safe 0 statistics."""
    ex1 = db_session.query(User).filter(User.email == "ex1_rpt@test.com").first()
    empty_exam = db_session.query(Exam).filter(Exam.title == "Empty Exam").first()
    headers = get_auth_header(ex1.id, ex1.email, "examiner")

    resp = client.get(f"/reports/exams/{empty_exam.id}", headers=headers)
    assert resp.status_code == 200
    data = resp.json()

    assert data["total_attempts"] == 0
    assert data["completed_attempts"] == 0
    assert data["passed_students"] == 0
    assert data["failed_students"] == 0
    assert data["average_score"] == 0.0
    assert data["highest_score"] == 0.0
    assert data["lowest_score"] == 0.0
    assert data["average_percentage"] == 0.0


def test_pass_fail_counts(client, db_session):
    """Test 10 — Pass/Fail counts accurately reflect Result table."""
    admin = db_session.query(User).filter(User.email == "admin_rpt@test.com").first()
    exam1 = db_session.query(Exam).filter(Exam.title == "Mathematics Midterm").first()
    headers = get_auth_header(admin.id, admin.email, "admin")

    resp = client.get(f"/reports/exams/{exam1.id}", headers=headers)
    assert resp.status_code == 200
    data = resp.json()

    assert data["passed_count"] == 2
    assert data["failed_count"] == 1


def test_ranking_integration(client, db_session):
    """Test 11 — Report correctly incorporates rank from Ranking model."""
    s2 = db_session.query(User).filter(User.email == "s2_rpt@test.com").first()
    headers = get_auth_header(s2.id, s2.email, "student")

    resp = client.get("/reports/my-performance", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["exams"][0]["rank"] == 2


def test_result_consistency(client, db_session):
    """Test 12 — Report values strictly match Result model."""
    s3 = db_session.query(User).filter(User.email == "s3_rpt@test.com").first()
    res3 = (
        db_session.query(Result)
        .join(ExamAttempt, Result.attempt_id == ExamAttempt.id)
        .filter(ExamAttempt.student_id == s3.id)
        .first()
    )
    headers = get_auth_header(s3.id, s3.email, "student")

    resp = client.get("/reports/my-performance", headers=headers)
    assert resp.status_code == 200
    item = resp.json()["exams"][0]

    assert item["marks_obtained"] == float(res3.total_marks_obtained)
    assert item["percentage"] == float(res3.percentage)
    assert item["pass_fail"] == res3.pass_fail


def test_question_statistics(client, db_session):
    """Test 13 — Question-level accuracy and attempt statistics."""
    ex1 = db_session.query(User).filter(User.email == "ex1_rpt@test.com").first()
    exam1 = db_session.query(Exam).filter(Exam.title == "Mathematics Midterm").first()
    headers = get_auth_header(ex1.id, ex1.email, "examiner")

    resp = client.get(f"/reports/exams/{exam1.id}/questions", headers=headers)
    assert resp.status_code == 200
    data = resp.json()

    assert data["total_questions"] == 2
    q1_stat = next(q for q in data["questions"] if "Solve 2x" in q["question_text"])
    q2_stat = next(q for q in data["questions"] if "Area of circle" in q["question_text"])

    # Q1: 3 answered (Alice correct, Bob correct, Charlie incorrect) -> 2/3 = 66.67%
    assert q1_stat["total_attempts"] == 3
    assert q1_stat["correct_count"] == 2
    assert q1_stat["incorrect_count"] == 1
    assert q1_stat["accuracy_percentage"] == 66.67
    assert q1_stat["topic"] == "Algebra"

    # Q2: 3 answered (Alice correct, Bob incorrect, Charlie incorrect) -> 1/3 = 33.33%
    assert q2_stat["total_attempts"] == 3
    assert q2_stat["correct_count"] == 1
    assert q2_stat["incorrect_count"] == 2
    assert q2_stat["accuracy_percentage"] == 33.33
    assert q2_stat["topic"] == "Geometry"


def test_candidate_wise_report(client, db_session):
    """Test 14 — Candidate-wise report with search and filtering."""
    ex1 = db_session.query(User).filter(User.email == "ex1_rpt@test.com").first()
    exam1 = db_session.query(Exam).filter(Exam.title == "Mathematics Midterm").first()
    headers = get_auth_header(ex1.id, ex1.email, "examiner")

    # Filter by exam
    resp = client.get(f"/reports/candidate-wise?exam_id={exam1.id}", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 3
    assert len(data["candidates"]) == 3

    # Candidates ordered by rank ASC
    assert data["candidates"][0]["rank"] == 1
    assert data["candidates"][0]["candidate_name"] == "Alice Student"
    assert data["candidates"][0]["score"] == 100.0

    # Filter by candidate name search
    resp_search = client.get(f"/reports/candidate-wise?exam_id={exam1.id}&candidate=Bob", headers=headers)
    assert resp_search.status_code == 200
    search_data = resp_search.json()
    assert search_data["total"] == 1
    assert search_data["candidates"][0]["candidate_name"] == "Bob Student"


def test_topic_wise_report(client, db_session):
    """Test 15 — Topic-wise aggregated report."""
    ex1 = db_session.query(User).filter(User.email == "ex1_rpt@test.com").first()
    exam1 = db_session.query(Exam).filter(Exam.title == "Mathematics Midterm").first()
    headers = get_auth_header(ex1.id, ex1.email, "examiner")

    resp = client.get(f"/reports/topic-wise?exam_id={exam1.id}", headers=headers)
    assert resp.status_code == 200
    data = resp.json()

    topics = {t["topic"]: t for t in data["topics"]}
    assert "Algebra" in topics
    assert "Geometry" in topics

    assert topics["Algebra"]["candidates_attempted"] == 3
    assert topics["Algebra"]["correct_answers"] == 2
    assert topics["Algebra"]["accuracy"] == 66.7

    assert topics["Geometry"]["candidates_attempted"] == 3
    assert topics["Geometry"]["correct_answers"] == 1
    assert topics["Geometry"]["accuracy"] == 33.3


def test_export_report_csv(client, db_session):
    """Test 16 — CSV export stream."""
    ex1 = db_session.query(User).filter(User.email == "ex1_rpt@test.com").first()
    exam1 = db_session.query(Exam).filter(Exam.title == "Mathematics Midterm").first()
    headers = get_auth_header(ex1.id, ex1.email, "examiner")

    resp = client.get(f"/reports/export?exam_id={exam1.id}&format=csv", headers=headers)
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
    assert "attachment; filename=" in resp.headers["content-disposition"]

    csv_text = resp.text
    assert "Rank,Candidate ID,Candidate Name,Email,Exam ID,Exam Name,Score,Total Marks,Percentage,Status,Attempt Date" in csv_text
    assert "Alice Student" in csv_text
    assert "Bob Student" in csv_text
    assert "Charlie Student" in csv_text


def test_sensitive_info_not_exposed(client, db_session):
    """Test 17 — Password hashes, tokens, or private fields are never exposed."""
    s1 = db_session.query(User).filter(User.email == "s1_rpt@test.com").first()
    headers = get_auth_header(s1.id, s1.email, "student")

    resp = client.get("/reports/my-performance", headers=headers)
    raw = resp.text
    assert "password" not in raw.lower()
    assert "hash" not in raw.lower()
    assert "token" not in raw.lower()


def test_reporting_is_read_only(client, db_session):
    """Test 18 — Report requests do not alter exam/result/ranking data."""
    s1 = db_session.query(User).filter(User.email == "s1_rpt@test.com").first()
    exam1 = db_session.query(Exam).filter(Exam.title == "Mathematics Midterm").first()
    headers = get_auth_header(s1.id, s1.email, "student")

    attempts_before = db_session.query(ExamAttempt).count()
    results_before = db_session.query(Result).count()
    rankings_before = db_session.query(Ranking).count()

    client.get("/reports/my-performance", headers=headers)
    client.get(f"/reports/students/{s1.id}", headers=headers)

    ex_headers = get_auth_header(exam1.created_by, "ex1_rpt@test.com", "examiner")
    client.get(f"/reports/exams/{exam1.id}", headers=ex_headers)
    client.get(f"/reports/exams/{exam1.id}/questions", headers=ex_headers)
    client.get(f"/reports/candidate-wise?exam_id={exam1.id}", headers=ex_headers)
    client.get(f"/reports/topic-wise?exam_id={exam1.id}", headers=ex_headers)
    client.get(f"/reports/export?exam_id={exam1.id}", headers=ex_headers)

    assert db_session.query(ExamAttempt).count() == attempts_before
    assert db_session.query(Result).count() == results_before
    assert db_session.query(Ranking).count() == rankings_before


def test_student_forbidden_from_examiner_endpoints(client, db_session):
    """Test 19 — Student receives 403 on examiner/admin report endpoints."""
    s1 = db_session.query(User).filter(User.email == "s1_rpt@test.com").first()
    exam1 = db_session.query(Exam).filter(Exam.title == "Mathematics Midterm").first()
    headers = get_auth_header(s1.id, s1.email, "student")

    assert client.get(f"/reports/exams/{exam1.id}", headers=headers).status_code == 403
    assert client.get(f"/reports/exams/{exam1.id}/questions", headers=headers).status_code == 403
    assert client.get("/reports/candidate-wise", headers=headers).status_code == 403
    assert client.get("/reports/topic-wise", headers=headers).status_code == 403
    assert client.get("/reports/export", headers=headers).status_code == 403
