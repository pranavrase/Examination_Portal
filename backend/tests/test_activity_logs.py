"""
test_activity_logs.py — Module 2.13: Activity Logging Service Tests
===================================================================
Tests verify:
  1. Create activity log: valid activity is recorded in DB.
  2. Authenticated user association: correct user_id linked.
  3. System activity: system-generated events handled (user_id=None).
  4. Login activity: successful and failed logins logged without passwords.
  5. Exam activity: exam start and exam submit logged.
  6. Auto-submit: auto-submission creates audit entry.
  7. Result activity: result_calculated logged upon scoring.
  8. Ranking activity: ranking_generated logged upon ranking calculation.
  9. Student authorization: students cannot access other students' logs (403).
 10. Admin access: admin can view all logs via /activity-logs.
 11. Examiner access: examiner can access authorized examination logs.
 12. Pagination: page and page_size mechanics.
 13. Filtering: action, entity_type, entity_id, dates filter correctly.
 14. Immutability: PUT and DELETE are rejected (405 Method Not Allowed).
 15. Sensitive information: passwords and tokens are sanitized and never stored.
 16. Timestamp integrity: server-generated timestamps are recorded.
 17. Large dataset: paginated DB-level retrieval works efficiently.
 18. Invalid entity: non-existent log ID returns 404.
"""

import pytest
from datetime import datetime, timezone, timedelta

from app.models.user import User
from app.models.role import Role
from app.models.log import ActivityLog
from app.models.exam import Exam, ExamSettings, ExamAssignment
from app.models.question import Question, QuestionCategory, McqOption, ExamQuestion
from app.models.attempt import ExamAttempt, AttemptAnswer
from app.models.result import Result
from app.core.security import hash_password, create_access_token
from app.services.role_service import seed_default_roles
from app.services.activity_log_service import (
    log_activity,
    get_activity_logs,
    get_activity_log_by_id,
    sanitize_data,
    utc_now,
)
from app.services.exam_attempt_service import start_attempt, submit_attempt, auto_submit_expired_attempts
from app.services.result_service import calculate_final_score
from app.services.ranking_service import compute_rankings_for_exam


def get_auth_header(user_id: int, email: str, role: str) -> dict:
    token = create_access_token(user_id=user_id, email=email, role=role)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def setup_activity_log_fixtures(db_session):
    """Seed default roles and baseline users."""
    seed_default_roles(db_session)

    student_role = db_session.query(Role).filter(Role.name == "student").first()
    examiner_role = db_session.query(Role).filter(Role.name == "examiner").first()
    admin_role = db_session.query(Role).filter(Role.name == "admin").first()

    admin = User(
        email="admin@example.com",
        full_name="Admin User",
        password_hash=hash_password("adminpass123"),
        is_active=True,
    )
    admin.roles.append(admin_role)

    examiner = User(
        email="examiner@example.com",
        full_name="Examiner User",
        password_hash=hash_password("examinerpass123"),
        is_active=True,
    )
    examiner.roles.append(examiner_role)

    student1 = User(
        email="student1@example.com",
        full_name="Alice Student",
        password_hash=hash_password("studentpass123"),
        is_active=True,
    )
    student1.roles.append(student_role)

    student2 = User(
        email="student2@example.com",
        full_name="Bob Student",
        password_hash=hash_password("studentpass123"),
        is_active=True,
    )
    student2.roles.append(student_role)

    db_session.add_all([admin, examiner, student1, student2])
    db_session.commit()


# ===========================================================================
# Test 1: Create activity log
# ===========================================================================
def test_01_create_activity_log(db_session):
    student = db_session.query(User).filter(User.email == "student1@example.com").first()
    log = log_activity(
        db=db_session,
        action="login_success",
        user_id=student.id,
        entity_type="user",
        entity_id=student.id,
        description="User logged in successfully",
        metadata={"client": "web"},
    )
    assert log is not None
    assert log.id is not None
    assert log.action_type == "login_success"
    assert log.action == "login_success"
    assert log.user_id == student.id
    assert log.entity_type == "user"
    assert log.entity_id == str(student.id)
    assert log.description == "User logged in successfully"


# ===========================================================================
# Test 2: Authenticated user association
# ===========================================================================
def test_02_authenticated_user_association(db_session):
    student = db_session.query(User).filter(User.email == "student1@example.com").first()
    log = log_activity(
        db=db_session,
        action="exam_start",
        user_id=student.id,
        entity_type="exam",
        entity_id="101",
        description="Exam started",
    )
    assert log.user_id == student.id
    assert log.user is not None
    assert log.user.email == "student1@example.com"


# ===========================================================================
# Test 3: System activity (nullable user_id)
# ===========================================================================
def test_03_system_activity(db_session):
    log = log_activity(
        db=db_session,
        action="system",
        user_id=None,
        entity_type="server",
        description="Automated maintenance cycle completed",
    )
    assert log is not None
    assert log.user_id is None
    assert log.action == "system"


# ===========================================================================
# Test 4: Login activity (login_success & login_failed)
# ===========================================================================
def test_04_login_activity(client, db_session):
    # Valid login
    res = client.post(
        "/auth/login",
        json={"email": "student1@example.com", "password": "studentpass123"},
    )
    assert res.status_code == 200

    success_log = (
        db_session.query(ActivityLog)
        .filter(ActivityLog.action_type == "login_success")
        .first()
    )
    assert success_log is not None
    assert success_log.user_id is not None

    # Failed login
    res_fail = client.post(
        "/auth/login",
        json={"email": "student1@example.com", "password": "wrongpassword!"},
    )
    assert res_fail.status_code == 401

    fail_log = (
        db_session.query(ActivityLog)
        .filter(ActivityLog.action_type == "login_failed")
        .first()
    )
    assert fail_log is not None
    # Password must never be present
    assert "wrongpassword!" not in str(fail_log.description)
    assert "wrongpassword!" not in str(fail_log.metadata_json)


# ===========================================================================
# Test 5: Exam activity (exam_start & exam_submit)
# ===========================================================================
def test_05_exam_activity(db_session):
    student = db_session.query(User).filter(User.email == "student1@example.com").first()
    examiner = db_session.query(User).filter(User.email == "examiner@example.com").first()

    exam = Exam(title="Activity Test Exam", created_by=examiner.id, status="published")
    settings = ExamSettings(duration_minutes=30, total_marks=100, passing_percentage=40)
    exam.settings = settings
    db_session.add(exam)
    db_session.flush()

    assignment = ExamAssignment(exam_id=exam.id, student_id=student.id)
    db_session.add(assignment)
    db_session.commit()

    # Start attempt
    start_res = start_attempt(db=db_session, exam_id=exam.id, current_user=student)
    att = start_res["attempt"]

    start_log = (
        db_session.query(ActivityLog)
        .filter(ActivityLog.user_id == student.id, ActivityLog.action_type == "exam_start")
        .first()
    )
    assert start_log is not None
    assert start_log.entity_id == str(att.id)

    # Submit attempt
    submit_attempt(db=db_session, attempt_id=att.id, current_user=student)

    submit_log = (
        db_session.query(ActivityLog)
        .filter(ActivityLog.user_id == student.id, ActivityLog.action_type == "exam_submit")
        .first()
    )
    assert submit_log is not None


# ===========================================================================
# Test 6: Auto-submit activity
# ===========================================================================
def test_06_auto_submit_activity(db_session):
    student = db_session.query(User).filter(User.email == "student1@example.com").first()
    examiner = db_session.query(User).filter(User.email == "examiner@example.com").first()

    exam = Exam(title="Auto-Submit Test Exam", created_by=examiner.id, status="published")
    exam.settings = ExamSettings(duration_minutes=1, total_marks=100, passing_percentage=40)
    db_session.add(exam)
    db_session.flush()

    # Past attempt that has expired
    past_started = utc_now() - timedelta(minutes=10)
    attempt = ExamAttempt(
        exam_id=exam.id,
        student_id=student.id,
        started_at=past_started,
        status="in_progress",
        remaining_seconds_snapshot=0,
    )
    db_session.add(attempt)
    db_session.commit()

    count = auto_submit_expired_attempts(db=db_session)
    assert count == 1

    auto_log = (
        db_session.query(ActivityLog)
        .filter(ActivityLog.user_id == student.id, ActivityLog.action_type.in_(["exam_auto_submitted", "exam_submit"]))
        .order_by(ActivityLog.id.desc())
        .first()
    )
    assert auto_log is not None


# ===========================================================================
# Test 7: Result activity
# ===========================================================================
def test_07_result_activity(db_session):
    student = db_session.query(User).filter(User.email == "student1@example.com").first()
    examiner = db_session.query(User).filter(User.email == "examiner@example.com").first()

    exam = Exam(title="Scoring Test Exam", created_by=examiner.id, status="published")
    exam.settings = ExamSettings(duration_minutes=60, total_marks=10, passing_percentage=40)
    db_session.add(exam)
    db_session.flush()

    attempt = ExamAttempt(
        exam_id=exam.id,
        student_id=student.id,
        started_at=utc_now(),
        submitted_at=utc_now(),
        status="submitted",
    )
    db_session.add(attempt)
    db_session.commit()

    calculate_final_score(db=db_session, attempt_id=attempt.id)

    res_log = (
        db_session.query(ActivityLog)
        .filter(ActivityLog.action_type == "result_calculated", ActivityLog.user_id == student.id)
        .first()
    )
    assert res_log is not None
    assert res_log.entity_type == "exam_attempt"
    assert res_log.entity_id == str(attempt.id)


# ===========================================================================
# Test 8: Ranking activity
# ===========================================================================
def test_08_ranking_activity(db_session):
    examiner = db_session.query(User).filter(User.email == "examiner@example.com").first()
    exam = Exam(title="Ranking Test Exam", created_by=examiner.id, status="published")
    db_session.add(exam)
    db_session.commit()

    compute_rankings_for_exam(exam_id=exam.id, db=db_session)

    rank_log = (
        db_session.query(ActivityLog)
        .filter(ActivityLog.action_type == "ranking_generated", ActivityLog.entity_id == str(exam.id))
        .first()
    )
    assert rank_log is not None
    assert rank_log.entity_type == "exam"


# ===========================================================================
# Test 9: Student authorization (cannot access other student's logs)
# ===========================================================================
def test_09_student_authorization_forbidden(client, db_session):
    student1 = db_session.query(User).filter(User.email == "student1@example.com").first()
    student2 = db_session.query(User).filter(User.email == "student2@example.com").first()

    # Log for student2
    log_activity(
        db=db_session,
        action="login_success",
        user_id=student2.id,
        entity_type="user",
        description="Student 2 activity",
    )

    headers_student1 = get_auth_header(student1.id, student1.email, "student")

    # Student 1 attempts to query with user_id=student2.id -> 403
    res = client.get(f"/activity-logs?user_id={student2.id}", headers=headers_student1)
    assert res.status_code == 403

    # Student 1 attempts to access /users/{student2_id}/activity-logs -> 403
    res2 = client.get(f"/users/{student2.id}/activity-logs", headers=headers_student1)
    assert res2.status_code == 403


# ===========================================================================
# Test 10: Admin access (full access)
# ===========================================================================
def test_10_admin_access(client, db_session):
    admin = db_session.query(User).filter(User.email == "admin@example.com").first()
    student = db_session.query(User).filter(User.email == "student1@example.com").first()

    log_activity(
        db=db_session,
        action="login_success",
        user_id=student.id,
        description="Student login",
    )

    headers = get_auth_header(admin.id, admin.email, "admin")
    res = client.get("/activity-logs", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    assert data["total"] >= 1


# ===========================================================================
# Test 11: Examiner access
# ===========================================================================
def test_11_examiner_access(client, db_session):
    examiner = db_session.query(User).filter(User.email == "examiner@example.com").first()
    student = db_session.query(User).filter(User.email == "student1@example.com").first()

    log_activity(
        db=db_session,
        action="exam_submit",
        user_id=student.id,
        entity_type="exam_attempt",
        description="Student submitted attempt",
    )

    headers = get_auth_header(examiner.id, examiner.email, "examiner")
    res = client.get(f"/activity-logs?user_id={student.id}", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 1


# ===========================================================================
# Test 12: Pagination
# ===========================================================================
def test_12_pagination(client, db_session):
    admin = db_session.query(User).filter(User.email == "admin@example.com").first()

    # Create 5 logs
    for i in range(5):
        log_activity(
            db=db_session,
            action="login_success",
            user_id=admin.id,
            description=f"Log item {i}",
        )

    headers = get_auth_header(admin.id, admin.email, "admin")
    res = client.get("/activity-logs?page=1&page_size=2", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert len(data["items"]) == 2
    assert data["page"] == 1
    assert data["page_size"] == 2
    assert data["total"] >= 5


# ===========================================================================
# Test 13: Filtering
# ===========================================================================
def test_13_filtering(client, db_session):
    admin = db_session.query(User).filter(User.email == "admin@example.com").first()
    student = db_session.query(User).filter(User.email == "student1@example.com").first()

    log_activity(
        db=db_session,
        action="exam_created",
        user_id=admin.id,
        entity_type="exam",
        entity_id="999",
        description="Created Exam #999",
    )
    log_activity(
        db=db_session,
        action="login_success",
        user_id=student.id,
        entity_type="user",
        entity_id=str(student.id),
        description="Student logged in",
    )

    headers = get_auth_header(admin.id, admin.email, "admin")

    # Filter by action
    res = client.get("/activity-logs?action=exam_created", headers=headers)
    assert res.status_code == 200
    data = res.json()
    for item in data["items"]:
        assert item["action"] == "exam_created"

    # Filter by entity_type & entity_id
    res2 = client.get("/activity-logs?entity_type=exam&entity_id=999", headers=headers)
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["total"] == 1
    assert data2["items"][0]["entity_id"] == "999"


# ===========================================================================
# Test 14: Immutability (PUT / DELETE rejected)
# ===========================================================================
def test_14_immutability(client, db_session):
    admin = db_session.query(User).filter(User.email == "admin@example.com").first()
    log = log_activity(
        db=db_session,
        action="login_success",
        user_id=admin.id,
        description="Original log entry",
    )

    headers = get_auth_header(admin.id, admin.email, "admin")

    # PUT request should return 405 Method Not Allowed
    put_res = client.put(f"/activity-logs/{log.id}", json={"description": "Hacked log"}, headers=headers)
    assert put_res.status_code == 405

    # DELETE request should return 405 Method Not Allowed
    del_res = client.delete(f"/activity-logs/{log.id}", headers=headers)
    assert del_res.status_code == 405


# ===========================================================================
# Test 15: Sensitive information protection
# ===========================================================================
def test_15_sensitive_info_protection(db_session):
    sensitive_dict = {
        "user_email": "user@example.com",
        "password": "supersecretpassword",
        "access_token": "eyJhbGciOi...",
        "api_key": "sk-12345",
        "nested": {
            "refresh_token": "rt_secret_token",
            "safe_field": "ok_value",
        },
    }
    sanitized = sanitize_data(sensitive_dict)
    assert sanitized["password"] == "[REDACTED]"
    assert sanitized["access_token"] == "[REDACTED]"
    assert sanitized["api_key"] == "[REDACTED]"
    assert sanitized["nested"]["refresh_token"] == "[REDACTED]"
    assert sanitized["nested"]["safe_field"] == "ok_value"

    # Verify when logging via log_activity
    student = db_session.query(User).filter(User.email == "student1@example.com").first()
    log = log_activity(
        db=db_session,
        action="login_success",
        user_id=student.id,
        metadata=sensitive_dict,
    )
    assert log.metadata_json["password"] == "[REDACTED]"
    assert log.metadata_json["access_token"] == "[REDACTED]"


# ===========================================================================
# Test 16: Timestamp integrity
# ===========================================================================
def test_16_timestamp_integrity(db_session):
    before = utc_now()
    log = log_activity(
        db=db_session,
        action="system",
        description="Automated server heartbeat",
    )
    after = utc_now()

    assert log.created_at is not None
    assert log.occurred_at is not None
    assert before <= log.created_at <= after + timedelta(seconds=1)


# ===========================================================================
# Test 17: Large dataset pagination
# ===========================================================================
def test_17_large_dataset_pagination(client, db_session):
    admin = db_session.query(User).filter(User.email == "admin@example.com").first()

    # Bulk insert 25 activity records
    for i in range(25):
        log_activity(
            db=db_session,
            action="login_success",
            user_id=admin.id,
            description=f"Batch log record {i}",
        )

    headers = get_auth_header(admin.id, admin.email, "admin")

    res_p1 = client.get("/activity-logs?page=1&page_size=10", headers=headers)
    assert res_p1.status_code == 200
    d1 = res_p1.json()
    assert len(d1["items"]) == 10
    assert d1["page"] == 1
    assert d1["total"] >= 25

    res_p3 = client.get("/activity-logs?page=3&page_size=10", headers=headers)
    assert res_p3.status_code == 200
    d3 = res_p3.json()
    assert len(d3["items"]) >= 5
    assert d3["page"] == 3


# ===========================================================================
# Test 18: Invalid entity reference (non-existent log ID)
# ===========================================================================
def test_18_invalid_log_id_returns_404(client, db_session):
    admin = db_session.query(User).filter(User.email == "admin@example.com").first()
    headers = get_auth_header(admin.id, admin.email, "admin")

    res = client.get("/activity-logs/9999999", headers=headers)
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()
