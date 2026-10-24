"""
test_security_monitoring.py — Module 2.14: Security Monitoring Service Tests
===========================================================================
Tests verify:
  1. Record security event: valid security event is saved.
  2. Persistence & retrieval: event persists in DB and is retrievable by ID.
  3. Failed login: single failed login produces a LOW severity event.
  4. Repeated failed login: multiple failed logins escalate to MEDIUM.
  5. Unauthorized access: access denied attempts record an event.
  6. Cross-user attempt access: accessing another student's attempt produces HIGH event.
  7. Expired attempt access: accessing expired attempt produces MEDIUM event.
  8. Unauthorized submission: submitting another student's attempt produces HIGH event.
  9. Normal auto-save: valid student auto-save produces zero security alerts.
 10. Suspicious auto-save: unauthorized attempt auto-save records security event.
 11. Admin access: admin can view /security/events.
 12. Student forbidden: student cannot access /security/events (403).
 13. Examiner forbidden: examiner cannot access /security/events (403).
 14. Filtering: filter by event_type, severity, user_id.
 15. Pagination: pagination page and page_size mechanics work correctly.
 16. Immutability: PUT and DELETE return 405 Method Not Allowed.
 17. Sensitive info sanitization: passwords and tokens are sanitized/redacted.
 18. Deterministic severity: severity maps deterministically.
 19. Cooldown deduplication: identical events within cooldown are deduplicated.
"""

import pytest
from datetime import datetime, timezone, timedelta

from app.models.user import User
from app.models.role import Role
from app.models.security import SecurityEvent
from app.models.exam import Exam, ExamSettings, ExamAssignment
from app.models.question import Question, QuestionCategory, McqOption, ExamQuestion
from app.models.attempt import ExamAttempt, AttemptAnswer
from app.core.security import hash_password, create_access_token
from app.services.role_service import seed_default_roles
from app.services.security_monitoring import (
    record_security_event,
    get_security_events,
    get_security_event_by_id,
    track_failed_login,
    sanitize_security_data,
    EVENT_SEVERITY_MAP,
)
from app.services.exam_attempt_service import start_attempt, submit_attempt


def get_auth_header(user_id: int, email: str, role: str) -> dict:
    token = create_access_token(user_id=user_id, email=email, role=role)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def setup_security_fixtures(db_session):
    """Seed default roles and baseline users."""
    seed_default_roles(db_session)

    student_role = db_session.query(Role).filter(Role.name == "student").first()
    examiner_role = db_session.query(Role).filter(Role.name == "examiner").first()
    admin_role = db_session.query(Role).filter(Role.name == "admin").first()

    # Admin user
    admin_user = db_session.query(User).filter(User.email == "sec_admin@example.com").first()
    if not admin_user:
        admin_user = User(
            email="sec_admin@example.com",
            password_hash=hash_password("AdminPass123!"),
            full_name="SecAdmin User",
            is_active=True,
            is_verified=True,
        )
        admin_user.roles.append(admin_role)
        db_session.add(admin_user)

    # Examiner user
    examiner_user = db_session.query(User).filter(User.email == "sec_examiner@example.com").first()
    if not examiner_user:
        examiner_user = User(
            email="sec_examiner@example.com",
            password_hash=hash_password("ExaminerPass123!"),
            full_name="SecExaminer User",
            is_active=True,
            is_verified=True,
        )
        examiner_user.roles.append(examiner_role)
        db_session.add(examiner_user)

    # Student 1
    student1 = db_session.query(User).filter(User.email == "sec_student1@example.com").first()
    if not student1:
        student1 = User(
            email="sec_student1@example.com",
            password_hash=hash_password("StudentPass123!"),
            full_name="Student One",
            is_active=True,
            is_verified=True,
        )
        student1.roles.append(student_role)
        db_session.add(student1)

    # Student 2
    student2 = db_session.query(User).filter(User.email == "sec_student2@example.com").first()
    if not student2:
        student2 = User(
            email="sec_student2@example.com",
            password_hash=hash_password("StudentPass123!"),
            full_name="Student Two",
            is_active=True,
            is_verified=True,
        )
        student2.roles.append(student_role)
        db_session.add(student2)

    db_session.commit()


# ---------------------------------------------------------------------------
# 1. Record Security Event
# ---------------------------------------------------------------------------
def test_01_record_security_event_valid(db_session):
    user = db_session.query(User).filter(User.email == "sec_student1@example.com").first()
    event = record_security_event(
        db=db_session,
        event_type="test_event",
        severity="LOW",
        user_id=user.id,
        entity_type="exam",
        entity_id="100",
        description="A test security event",
        ip_address="127.0.0.1",
        metadata={"detail": "sample"},
    )
    assert event.id is not None
    assert event.event_type == "test_event"
    assert event.severity == "LOW"
    assert event.user_id == user.id


# ---------------------------------------------------------------------------
# 2. Persistence & Retrieval
# ---------------------------------------------------------------------------
def test_02_security_event_persistence_and_retrieval(db_session):
    event = record_security_event(
        db=db_session,
        event_type="persistence_test",
        severity="MEDIUM",
        description="Verify persistence in database",
    )
    retrieved = get_security_event_by_id(db=db_session, event_id=event.id)
    assert retrieved is not None
    assert retrieved.id == event.id
    assert retrieved.event_type == "persistence_test"
    assert retrieved.severity == "MEDIUM"


# ---------------------------------------------------------------------------
# 3. Failed Login Event (LOW)
# ---------------------------------------------------------------------------
def test_03_failed_login_creates_low_severity_event(client, db_session):
    response = client.post("/auth/login", json={"email": "sec_student1@example.com", "password": "WrongPassword123!"})
    assert response.status_code == 401

    event = (
        db_session.query(SecurityEvent)
        .filter(SecurityEvent.event_type == "failed_login")
        .order_by(SecurityEvent.created_at.desc())
        .first()
    )
    assert event is not None
    assert event.severity == "LOW"
    assert event.description is not None
    assert "WrongPassword" not in str(event.metadata_json)


# ---------------------------------------------------------------------------
# 4. Repeated Failed Login Escalates to MEDIUM
# ---------------------------------------------------------------------------
def test_04_repeated_failed_login_escalates_to_medium(client, db_session):
    # Attempt 3 failed logins in rapid succession
    for _ in range(3):
        client.post("/auth/login", json={"email": "sec_student1@example.com", "password": "WrongPassword123!"})

    repeated_event = (
        db_session.query(SecurityEvent)
        .filter(SecurityEvent.event_type == "repeated_failed_login")
        .order_by(SecurityEvent.created_at.desc())
        .first()
    )
    assert repeated_event is not None
    assert repeated_event.severity == "MEDIUM"


# ---------------------------------------------------------------------------
# 5. Unauthorized Access Event
# ---------------------------------------------------------------------------
def test_05_unauthorized_access_security_event(db_session):
    user = db_session.query(User).filter(User.email == "sec_student1@example.com").first()
    event = record_security_event(
        db=db_session,
        event_type="unauthorized_access",
        severity="HIGH",
        user_id=user.id,
        entity_type="endpoint",
        description="Attempt to access admin resource",
    )
    assert event.event_type == "unauthorized_access"
    assert event.severity == "HIGH"


# ---------------------------------------------------------------------------
# 6. Cross-User Attempt Access (HIGH)
# ---------------------------------------------------------------------------
def test_06_cross_user_attempt_access(client, db_session):
    student1 = db_session.query(User).filter(User.email == "sec_student1@example.com").first()
    student2 = db_session.query(User).filter(User.email == "sec_student2@example.com").first()
    admin = db_session.query(User).filter(User.email == "sec_admin@example.com").first()

    # Create exam and attempt for student1
    exam = Exam(
        title="Sec Test Exam 1",
        description="Security test exam",
        created_by=admin.id,
        status="published",
    )
    db_session.add(exam)
    db_session.flush()

    settings = ExamSettings(
        exam_id=exam.id,
        duration_minutes=30,
        total_marks=100.0,
        passing_percentage=40.0,
    )
    db_session.add(settings)

    assignment = ExamAssignment(
        exam_id=exam.id,
        student_id=student1.id,
    )
    db_session.add(assignment)
    db_session.commit()

    attempt = start_attempt(db=db_session, exam_id=exam.id, current_user=student1)["attempt"]

    # Student 2 tries to view remaining time of Student 1's attempt
    auth2 = get_auth_header(student2.id, student2.email, "student")
    res = client.get(f"/exam-attempts/{attempt.id}/remaining-time", headers=auth2)
    assert res.status_code == 403

    event = (
        db_session.query(SecurityEvent)
        .filter(SecurityEvent.event_type == "cross_user_access_attempt")
        .order_by(SecurityEvent.created_at.desc())
        .first()
    )
    assert event is not None
    assert event.severity == "HIGH"
    assert event.user_id == student2.id


# ---------------------------------------------------------------------------
# 7. Expired Attempt Access (MEDIUM)
# ---------------------------------------------------------------------------
def test_07_expired_attempt_access(client, db_session):
    student1 = db_session.query(User).filter(User.email == "sec_student1@example.com").first()
    admin = db_session.query(User).filter(User.email == "sec_admin@example.com").first()

    exam = Exam(title="Sec Expired Exam", created_by=admin.id, status="published")
    db_session.add(exam)
    db_session.flush()
    settings = ExamSettings(exam_id=exam.id, duration_minutes=1, total_marks=50.0, passing_percentage=40.0)
    db_session.add(settings)
    db_session.add(ExamAssignment(exam_id=exam.id, student_id=student1.id))
    db_session.commit()

    attempt = start_attempt(db=db_session, exam_id=exam.id, current_user=student1)["attempt"]
    # Mark submitted
    attempt.status = "submitted"
    db_session.commit()

    auth1 = get_auth_header(student1.id, student1.email, "student")
    # Trying to submit already submitted attempt
    res = client.post(f"/exam-attempts/{attempt.id}/submit", headers=auth1)
    assert res.status_code == 409

    event = (
        db_session.query(SecurityEvent)
        .filter(SecurityEvent.event_type == "attempt_after_expiration")
        .order_by(SecurityEvent.created_at.desc())
        .first()
    )
    assert event is not None
    assert event.severity == "MEDIUM"


# ---------------------------------------------------------------------------
# 8. Unauthorized Submission (HIGH)
# ---------------------------------------------------------------------------
def test_08_unauthorized_submission(client, db_session):
    student1 = db_session.query(User).filter(User.email == "sec_student1@example.com").first()
    student2 = db_session.query(User).filter(User.email == "sec_student2@example.com").first()
    admin = db_session.query(User).filter(User.email == "sec_admin@example.com").first()

    exam = Exam(title="Sec Sub Exam", created_by=admin.id, status="published")
    db_session.add(exam)
    db_session.flush()
    settings = ExamSettings(exam_id=exam.id, duration_minutes=60, total_marks=50.0, passing_percentage=40.0)
    db_session.add(settings)
    db_session.add(ExamAssignment(exam_id=exam.id, student_id=student1.id))
    db_session.commit()

    attempt = start_attempt(db=db_session, exam_id=exam.id, current_user=student1)["attempt"]

    # Student 2 tries to submit Student 1's attempt
    auth2 = get_auth_header(student2.id, student2.email, "student")
    res = client.post(f"/exam-attempts/{attempt.id}/submit", headers=auth2)
    assert res.status_code == 403

    event = (
        db_session.query(SecurityEvent)
        .filter(SecurityEvent.event_type == "unauthorized_submission")
        .order_by(SecurityEvent.created_at.desc())
        .first()
    )
    assert event is not None
    assert event.severity == "HIGH"
    assert event.user_id == student2.id


# ---------------------------------------------------------------------------
# 9. Normal Auto-Save Generates Zero Security Alerts
# ---------------------------------------------------------------------------
def test_09_normal_autosave_generates_zero_security_alerts(client, db_session):
    student1 = db_session.query(User).filter(User.email == "sec_student1@example.com").first()
    admin = db_session.query(User).filter(User.email == "sec_admin@example.com").first()

    exam = Exam(title="Sec Normal Autosave Exam", created_by=admin.id, status="published")
    db_session.add(exam)
    db_session.flush()
    settings = ExamSettings(exam_id=exam.id, duration_minutes=60, total_marks=50.0, passing_percentage=40.0)
    db_session.add(settings)
    db_session.add(ExamAssignment(exam_id=exam.id, student_id=student1.id))
    db_session.commit()

    attempt = start_attempt(db=db_session, exam_id=exam.id, current_user=student1)["attempt"]

    sec_count_before = db_session.query(SecurityEvent).count()

    auth1 = get_auth_header(student1.id, student1.email, "student")
    res = client.put(
        f"/exam-attempts/{attempt.id}/answers/autosave",
        json={"question_id": 9999, "selected_option_id": 1},
        headers=auth1,
    )
    # Valid attempt check passes
    sec_count_after = db_session.query(SecurityEvent).count()
    assert sec_count_after == sec_count_before


# ---------------------------------------------------------------------------
# 10. Suspicious Auto-Save Detected
# ---------------------------------------------------------------------------
def test_10_suspicious_autosave_detected(client, db_session):
    student1 = db_session.query(User).filter(User.email == "sec_student1@example.com").first()
    student2 = db_session.query(User).filter(User.email == "sec_student2@example.com").first()
    admin = db_session.query(User).filter(User.email == "sec_admin@example.com").first()

    exam = Exam(title="Sec Suspicious Autosave Exam", created_by=admin.id, status="published")
    db_session.add(exam)
    db_session.flush()
    settings = ExamSettings(exam_id=exam.id, duration_minutes=60, total_marks=50.0, passing_percentage=40.0)
    db_session.add(settings)
    db_session.add(ExamAssignment(exam_id=exam.id, student_id=student1.id))
    db_session.commit()

    attempt = start_attempt(db=db_session, exam_id=exam.id, current_user=student1)["attempt"]

    # Student 2 tries to autosave Student 1's attempt
    auth2 = get_auth_header(student2.id, student2.email, "student")
    res = client.put(
        f"/exam-attempts/{attempt.id}/answers/autosave",
        json={"question_id": 1, "selected_option_id": 1},
        headers=auth2,
    )
    assert res.status_code == 403

    event = (
        db_session.query(SecurityEvent)
        .filter(SecurityEvent.event_type == "cross_user_access_attempt")
        .order_by(SecurityEvent.created_at.desc())
        .first()
    )
    assert event is not None
    assert event.severity == "HIGH"
    assert event.user_id == student2.id


# ---------------------------------------------------------------------------
# 11. Admin Can Access /security/events
# ---------------------------------------------------------------------------
def test_11_admin_can_access_security_events(client, db_session):
    admin = db_session.query(User).filter(User.email == "sec_admin@example.com").first()
    auth = get_auth_header(admin.id, admin.email, "admin")
    res = client.get("/security/events", headers=auth)
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data


# ---------------------------------------------------------------------------
# 12. Student Forbidden from /security/events
# ---------------------------------------------------------------------------
def test_12_student_forbidden_from_security_events(client, db_session):
    student = db_session.query(User).filter(User.email == "sec_student1@example.com").first()
    auth = get_auth_header(student.id, student.email, "student")
    res = client.get("/security/events", headers=auth)
    assert res.status_code == 403


# ---------------------------------------------------------------------------
# 13. Examiner Forbidden from /security/events
# ---------------------------------------------------------------------------
def test_13_examiner_forbidden_from_security_events(client, db_session):
    examiner = db_session.query(User).filter(User.email == "sec_examiner@example.com").first()
    auth = get_auth_header(examiner.id, examiner.email, "examiner")
    res = client.get("/security/events", headers=auth)
    assert res.status_code == 403


# ---------------------------------------------------------------------------
# 14. Filtering of Security Events
# ---------------------------------------------------------------------------
def test_14_security_events_filtering(client, db_session):
    admin = db_session.query(User).filter(User.email == "sec_admin@example.com").first()
    auth = get_auth_header(admin.id, admin.email, "admin")

    record_security_event(
        db=db_session,
        event_type="filter_test_type",
        severity="CRITICAL",
        description="Filter test critical event",
    )

    res = client.get("/security/events?event_type=filter_test_type&severity=CRITICAL", headers=auth)
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 1
    for item in data["items"]:
        assert item["event_type"] == "filter_test_type"
        assert item["severity"] == "CRITICAL"


# ---------------------------------------------------------------------------
# 15. Pagination of Security Events
# ---------------------------------------------------------------------------
def test_15_security_events_pagination(client, db_session):
    admin = db_session.query(User).filter(User.email == "sec_admin@example.com").first()
    auth = get_auth_header(admin.id, admin.email, "admin")

    res = client.get("/security/events?page=1&page_size=2", headers=auth)
    assert res.status_code == 200
    data = res.json()
    assert data["page"] == 1
    assert data["page_size"] == 2
    assert len(data["items"]) <= 2


# ---------------------------------------------------------------------------
# 16. Immutability (PUT/DELETE Rejected)
# ---------------------------------------------------------------------------
def test_16_security_events_immutability(client, db_session):
    admin = db_session.query(User).filter(User.email == "sec_admin@example.com").first()
    auth = get_auth_header(admin.id, admin.email, "admin")

    res_put = client.put("/security/events", headers=auth, json={})
    assert res_put.status_code == 405

    res_delete = client.delete("/security/events", headers=auth)
    assert res_delete.status_code == 405


# ---------------------------------------------------------------------------
# 17. Sensitive Information Sanitized
# ---------------------------------------------------------------------------
def test_17_sensitive_info_sanitized(db_session):
    raw_meta = {
        "password": "SuperSecretPassword123!",
        "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.dummy",
        "api_key": "sk-1234567890abcdef",
        "safe_info": "Normal metadata text",
    }
    cleaned = sanitize_security_data(raw_meta)
    assert cleaned["password"] == "[REDACTED]"
    assert cleaned["token"] == "[REDACTED]"
    assert cleaned["api_key"] == "[REDACTED]"
    assert cleaned["safe_info"] == "Normal metadata text"


# ---------------------------------------------------------------------------
# 18. Deterministic Severity Classification
# ---------------------------------------------------------------------------
def test_18_deterministic_severity_classification(db_session):
    assert EVENT_SEVERITY_MAP["failed_login"] == "LOW"
    assert EVENT_SEVERITY_MAP["repeated_failed_login"] == "MEDIUM"
    assert EVENT_SEVERITY_MAP["unauthorized_access"] == "HIGH"
    assert EVENT_SEVERITY_MAP["cross_user_access_attempt"] == "HIGH"
    assert EVENT_SEVERITY_MAP["attempt_after_expiration"] == "MEDIUM"
    assert EVENT_SEVERITY_MAP["unauthorized_submission"] == "HIGH"

    event = record_security_event(db=db_session, event_type="failed_login")
    assert event.severity == "LOW"


# ---------------------------------------------------------------------------
# 19. Cooldown Deduplication Prevents Floods
# ---------------------------------------------------------------------------
def test_19_cooldown_deduplication_prevents_flood(db_session):
    user = db_session.query(User).filter(User.email == "sec_student1@example.com").first()

    event1 = record_security_event(
        db=db_session,
        event_type="flood_test",
        severity="LOW",
        user_id=user.id,
        entity_type="test",
        entity_id="1",
        cooldown_seconds=10,
    )

    event2 = record_security_event(
        db=db_session,
        event_type="flood_test",
        severity="LOW",
        user_id=user.id,
        entity_type="test",
        entity_id="1",
        cooldown_seconds=10,
    )

    assert event1.id == event2.id
