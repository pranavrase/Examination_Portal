"""
test_notifications.py — Module 2.15: Notification / Future Hooks Tests
======================================================================
Tests verify:
  1. Notification creation: valid notification is created and persisted.
  2. Recipient validation: invalid user_id raises 404.
  3. Type validation: invalid notification type raises 400.
  4. Idempotency: duplicate event_key returns existing notification without duplicates.
  5. Scoped retrieval: authenticated user retrieves only their own notifications.
  6. Isolation: user cannot see another user's notifications.
  7. Pagination: page and page_size mechanics, newest-first ordering.
  8. Filtering: filtering by is_read and notification_type.
  9. Unread count: /notifications/unread-count returns accurate count.
 10. Mark as read: PATCH /notifications/{id}/read marks notification as read with timestamp.
 11. Read idempotency: marking already-read notification returns 200 without error.
 12. Ownership protection: student cannot mark another student's notification as read (403).
 13. Mark all read: PATCH & POST /notifications/read-all marks all unread notifications read.
 14. Exam submission integration: auto-submission creates EXAM_AUTO_SUBMITTED notification.
 15. Auto-submission idempotency: duplicate auto-submission does not create duplicate notification.
 16. Result engine integration: score calculation creates RESULT_AVAILABLE notification.
 17. Result idempotency: recalculating result does not duplicate notification.
 18. Ranking engine integration: ranking computation creates RANKING_AVAILABLE notification.
 19. Security monitoring integration: repeated failed login creates SECURITY_ALERT notification.
 20. Future provider hooks: custom provider interface can be registered and dispatched to.
"""

import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal

from app.models.user import User
from app.models.role import Role
from app.models.notification import Notification, ALLOWED_NOTIFICATION_TYPES
from app.models.exam import Exam, ExamSettings, ExamAssignment
from app.models.question import Question, QuestionCategory, McqOption, ExamQuestion
from app.models.attempt import ExamAttempt, AttemptAnswer
from app.core.security import hash_password, create_access_token
from app.services.role_service import seed_default_roles
from app.services.notification_service import (
    create_notification,
    get_user_notifications,
    get_unread_count,
    mark_notification_read,
    mark_all_notifications_read,
    BaseNotificationProvider,
    dispatcher,
)
from app.services.exam_attempt_service import start_attempt, auto_submit_expired_attempts
from app.services.result_service import calculate_final_score
from app.services.ranking_service import compute_rankings_for_exam
from app.services.security_monitoring import track_failed_login


def get_auth_header(user_id: int, email: str, role: str) -> dict:
    token = create_access_token(user_id=user_id, email=email, role=role)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def setup_notification_fixtures(db_session):
    """Seed default roles and baseline users."""
    seed_default_roles(db_session)

    student_role = db_session.query(Role).filter(Role.name == "student").first()
    admin_role = db_session.query(Role).filter(Role.name == "admin").first()

    # Admin user
    admin_user = db_session.query(User).filter(User.email == "notif_admin@example.com").first()
    if not admin_user:
        admin_user = User(
            email="notif_admin@example.com",
            password_hash=hash_password("AdminPass123!"),
            full_name="Notif Admin",
            is_active=True,
            is_verified=True,
        )
        admin_user.roles.append(admin_role)
        db_session.add(admin_user)

    # Student 1
    student1 = db_session.query(User).filter(User.email == "notif_student1@example.com").first()
    if not student1:
        student1 = User(
            email="notif_student1@example.com",
            password_hash=hash_password("StudentPass123!"),
            full_name="Student One",
            is_active=True,
            is_verified=True,
        )
        student1.roles.append(student_role)
        db_session.add(student1)

    # Student 2
    student2 = db_session.query(User).filter(User.email == "notif_student2@example.com").first()
    if not student2:
        student2 = User(
            email="notif_student2@example.com",
            password_hash=hash_password("StudentPass123!"),
            full_name="Student Two",
            is_active=True,
            is_verified=True,
        )
        student2.roles.append(student_role)
        db_session.add(student2)

    db_session.commit()


# ---------------------------------------------------------------------------
# 1. Create Valid Notification
# ---------------------------------------------------------------------------
def test_01_create_valid_notification(db_session):
    student1 = db_session.query(User).filter(User.email == "notif_student1@example.com").first()
    notif = create_notification(
        db=db_session,
        user_id=student1.id,
        title="Welcome to Exams",
        message="Your account is activated and ready for exams.",
        notification_type="SYSTEM",
        entity_type="user",
        entity_id=str(student1.id),
    )
    assert notif.id is not None
    assert notif.user_id == student1.id
    assert notif.title == "Welcome to Exams"
    assert notif.is_read is False
    assert notif.read_at is None
    assert notif.notification_type == "SYSTEM"


# ---------------------------------------------------------------------------
# 2. Create Notification Invalid User
# ---------------------------------------------------------------------------
def test_02_create_notification_invalid_user(db_session):
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc_info:
        create_notification(
            db=db_session,
            user_id=999999,
            title="Ghost User",
            message="Message to nowhere",
            notification_type="SYSTEM",
        )
    assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# 3. Create Notification Invalid Type
# ---------------------------------------------------------------------------
def test_03_create_notification_invalid_type(db_session):
    student1 = db_session.query(User).filter(User.email == "notif_student1@example.com").first()
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc_info:
        create_notification(
            db=db_session,
            user_id=student1.id,
            title="Bad Type",
            message="This type is invalid",
            notification_type="INVALID_RANDOM_TYPE",
        )
    assert exc_info.value.status_code == 400


# ---------------------------------------------------------------------------
# 4. Duplicate Event Key Idempotency
# ---------------------------------------------------------------------------
def test_04_duplicate_event_key_idempotency(db_session):
    student1 = db_session.query(User).filter(User.email == "notif_student1@example.com").first()
    event_key = "event_unique_xyz_123"

    notif1 = create_notification(
        db=db_session,
        user_id=student1.id,
        title="Exam Published",
        message="Exam has been published",
        notification_type="EXAM_PUBLISHED",
        event_key=event_key,
    )

    notif2 = create_notification(
        db=db_session,
        user_id=student1.id,
        title="Exam Published Again",
        message="Duplicate attempt",
        notification_type="EXAM_PUBLISHED",
        event_key=event_key,
    )

    assert notif1.id == notif2.id
    total = db_session.query(Notification).filter(Notification.event_key == event_key).count()
    assert total == 1


# ---------------------------------------------------------------------------
# 5. Authenticated User Gets Own Notifications
# ---------------------------------------------------------------------------
def test_05_authenticated_user_gets_own_notifications(client, db_session):
    student1 = db_session.query(User).filter(User.email == "notif_student1@example.com").first()
    create_notification(
        db=db_session,
        user_id=student1.id,
        title="Own Notification",
        message="Visible only to student 1",
        notification_type="SYSTEM",
    )

    auth1 = get_auth_header(student1.id, student1.email, "student")
    res = client.get("/notifications", headers=auth1)
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 1
    assert any(n["title"] == "Own Notification" for n in data["items"])


# ---------------------------------------------------------------------------
# 6. User Cannot Get Another User's Notifications
# ---------------------------------------------------------------------------
def test_06_user_cannot_get_another_users_notifications(client, db_session):
    student1 = db_session.query(User).filter(User.email == "notif_student1@example.com").first()
    student2 = db_session.query(User).filter(User.email == "notif_student2@example.com").first()

    create_notification(
        db=db_session,
        user_id=student1.id,
        title="Secret Notification for Student 1",
        message="Student 2 must not see this",
        notification_type="SECURITY_ALERT",
    )

    auth2 = get_auth_header(student2.id, student2.email, "student")
    res = client.get("/notifications", headers=auth2)
    assert res.status_code == 200
    data = res.json()
    for item in data["items"]:
        assert item["title"] != "Secret Notification for Student 1"
        assert item["user_id"] == student2.id


# ---------------------------------------------------------------------------
# 7. Pagination and Newest-First Ordering
# ---------------------------------------------------------------------------
def test_07_pagination_and_newest_first_ordering(client, db_session):
    student1 = db_session.query(User).filter(User.email == "notif_student1@example.com").first()
    for i in range(5):
        create_notification(
            db=db_session,
            user_id=student1.id,
            title=f"Notification #{i}",
            message=f"Body for notification {i}",
            notification_type="SYSTEM",
        )

    auth1 = get_auth_header(student1.id, student1.email, "student")
    res = client.get("/notifications?page=1&page_size=2", headers=auth1)
    assert res.status_code == 200
    data = res.json()
    assert data["page"] == 1
    assert data["page_size"] == 2
    assert len(data["items"]) == 2
    # Verify newest first
    assert data["items"][0]["id"] > data["items"][1]["id"]


# ---------------------------------------------------------------------------
# 8. Unread and Type Filtering
# ---------------------------------------------------------------------------
def test_08_unread_and_type_filtering(client, db_session):
    student1 = db_session.query(User).filter(User.email == "notif_student1@example.com").first()
    n_unread = create_notification(
        db=db_session,
        user_id=student1.id,
        title="Unread Alert",
        message="Unread",
        notification_type="SECURITY_ALERT",
    )
    n_read = create_notification(
        db=db_session,
        user_id=student1.id,
        title="Read Alert",
        message="Read",
        notification_type="SYSTEM",
    )
    mark_notification_read(db=db_session, notification_id=n_read.id, current_user=student1)

    auth1 = get_auth_header(student1.id, student1.email, "student")

    # Filter unread
    res_unread = client.get("/notifications?is_read=false", headers=auth1)
    assert res_unread.status_code == 200
    for item in res_unread.json()["items"]:
        assert item["is_read"] is False

    # Filter type
    res_type = client.get("/notifications?notification_type=SECURITY_ALERT", headers=auth1)
    assert res_type.status_code == 200
    for item in res_type.json()["items"]:
        assert item["notification_type"] == "SECURITY_ALERT"


# ---------------------------------------------------------------------------
# 9. Unread Count Endpoint
# ---------------------------------------------------------------------------
def test_09_unread_count_endpoint(client, db_session):
    student1 = db_session.query(User).filter(User.email == "notif_student1@example.com").first()
    # Clear prior
    db_session.query(Notification).filter(Notification.user_id == student1.id).delete()
    db_session.commit()

    create_notification(
        db=db_session,
        user_id=student1.id,
        title="Count 1",
        message="Msg",
        notification_type="SYSTEM",
    )
    create_notification(
        db=db_session,
        user_id=student1.id,
        title="Count 2",
        message="Msg",
        notification_type="SYSTEM",
    )

    auth1 = get_auth_header(student1.id, student1.email, "student")
    res = client.get("/notifications/unread-count", headers=auth1)
    assert res.status_code == 200
    assert res.json()["unread_count"] == 2


# ---------------------------------------------------------------------------
# 10. Mark Notification Read
# ---------------------------------------------------------------------------
def test_10_mark_notification_read(client, db_session):
    student1 = db_session.query(User).filter(User.email == "notif_student1@example.com").first()
    notif = create_notification(
        db=db_session,
        user_id=student1.id,
        title="To be read",
        message="Msg",
        notification_type="SYSTEM",
    )
    auth1 = get_auth_header(student1.id, student1.email, "student")
    res = client.patch(f"/notifications/{notif.id}/read", headers=auth1)
    assert res.status_code == 200
    data = res.json()
    assert data["is_read"] is True
    assert data["read_at"] is not None


# ---------------------------------------------------------------------------
# 11. Mark Already Read Notification is Idempotent
# ---------------------------------------------------------------------------
def test_11_mark_already_read_notification_is_idempotent(client, db_session):
    student1 = db_session.query(User).filter(User.email == "notif_student1@example.com").first()
    notif = create_notification(
        db=db_session,
        user_id=student1.id,
        title="Idempotency Test",
        message="Msg",
        notification_type="SYSTEM",
    )
    auth1 = get_auth_header(student1.id, student1.email, "student")
    res1 = client.patch(f"/notifications/{notif.id}/read", headers=auth1)
    assert res1.status_code == 200
    res2 = client.patch(f"/notifications/{notif.id}/read", headers=auth1)
    assert res2.status_code == 200
    assert res2.json()["is_read"] is True


# ---------------------------------------------------------------------------
# 12. Unauthorized Notification Read Access Forbidden
# ---------------------------------------------------------------------------
def test_12_unauthorized_user_cannot_mark_another_users_notification_read(client, db_session):
    student1 = db_session.query(User).filter(User.email == "notif_student1@example.com").first()
    student2 = db_session.query(User).filter(User.email == "notif_student2@example.com").first()

    notif1 = create_notification(
        db=db_session,
        user_id=student1.id,
        title="Student 1 only",
        message="Msg",
        notification_type="SYSTEM",
    )

    auth2 = get_auth_header(student2.id, student2.email, "student")
    res = client.patch(f"/notifications/{notif1.id}/read", headers=auth2)
    assert res.status_code == 403


# ---------------------------------------------------------------------------
# 13. Mark All Notifications Read
# ---------------------------------------------------------------------------
def test_13_mark_all_read_patch_and_post(client, db_session):
    student1 = db_session.query(User).filter(User.email == "notif_student1@example.com").first()
    for i in range(3):
        create_notification(
            db=db_session,
            user_id=student1.id,
            title=f"Unread {i}",
            message="Msg",
            notification_type="SYSTEM",
        )

    auth1 = get_auth_header(student1.id, student1.email, "student")
    # PATCH /notifications/read-all
    res_patch = client.patch("/notifications/read-all", headers=auth1)
    assert res_patch.status_code == 200
    assert res_patch.json()["updated_count"] >= 3

    # Add 2 more unread
    create_notification(db=db_session, user_id=student1.id, title="Unread 4", message="Msg", notification_type="SYSTEM")
    create_notification(db=db_session, user_id=student1.id, title="Unread 5", message="Msg", notification_type="SYSTEM")

    # POST /notifications/read-all
    res_post = client.post("/notifications/read-all", headers=auth1)
    assert res_post.status_code == 200
    assert res_post.json()["updated_count"] == 2

    # Verify unread count is now 0
    assert get_unread_count(db=db_session, user_id=student1.id) == 0


# ---------------------------------------------------------------------------
# 14. Exam Auto-Submission Generates Notification
# ---------------------------------------------------------------------------
def test_14_exam_auto_submission_generates_notification(client, db_session):
    student1 = db_session.query(User).filter(User.email == "notif_student1@example.com").first()
    admin = db_session.query(User).filter(User.email == "notif_admin@example.com").first()

    exam = Exam(title="Auto Submit Notif Exam", created_by=admin.id, status="published")
    db_session.add(exam)
    db_session.flush()
    settings = ExamSettings(exam_id=exam.id, duration_minutes=1, total_marks=50.0, passing_percentage=40.0)
    db_session.add(settings)
    db_session.add(ExamAssignment(exam_id=exam.id, student_id=student1.id))
    db_session.commit()

    attempt = start_attempt(db=db_session, exam_id=exam.id, current_user=student1)["attempt"]
    # Fast forward started_at by 2 minutes
    attempt.started_at = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=2)
    db_session.commit()

    count = auto_submit_expired_attempts(db=db_session)
    assert count >= 1

    notif = (
        db_session.query(Notification)
        .filter(
            Notification.user_id == student1.id,
            Notification.notification_type == "EXAM_AUTO_SUBMITTED",
        )
        .first()
    )
    assert notif is not None
    assert notif.title == "Exam Submitted"
    assert "automatically" in notif.message


# ---------------------------------------------------------------------------
# 15. Duplicate Auto-Submission Does Not Duplicate Notification
# ---------------------------------------------------------------------------
def test_15_duplicate_auto_submission_does_not_duplicate_notification(db_session):
    student1 = db_session.query(User).filter(User.email == "notif_student1@example.com").first()
    admin = db_session.query(User).filter(User.email == "notif_admin@example.com").first()

    exam = Exam(title="Auto Submit Idempotency Exam", created_by=admin.id, status="published")
    db_session.add(exam)
    db_session.flush()
    settings = ExamSettings(exam_id=exam.id, duration_minutes=1, total_marks=50.0, passing_percentage=40.0)
    db_session.add(settings)
    db_session.add(ExamAssignment(exam_id=exam.id, student_id=student1.id))
    db_session.commit()

    attempt = start_attempt(db=db_session, exam_id=exam.id, current_user=student1)["attempt"]
    attempt.started_at = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=2)
    db_session.commit()

    auto_submit_expired_attempts(db=db_session)
    auto_submit_expired_attempts(db=db_session)

    notif_count = (
        db_session.query(Notification)
        .filter(
            Notification.user_id == student1.id,
            Notification.notification_type == "EXAM_AUTO_SUBMITTED",
            Notification.entity_id == str(attempt.id),
        )
        .count()
    )
    assert notif_count == 1


# ---------------------------------------------------------------------------
# 16. Result Calculation Generates Notification
# ---------------------------------------------------------------------------
def test_16_result_calculation_generates_notification(db_session):
    student1 = db_session.query(User).filter(User.email == "notif_student1@example.com").first()
    admin = db_session.query(User).filter(User.email == "notif_admin@example.com").first()

    exam = Exam(title="Result Notif Exam", created_by=admin.id, status="published")
    db_session.add(exam)
    db_session.flush()
    settings = ExamSettings(exam_id=exam.id, duration_minutes=60, total_marks=50.0, passing_percentage=40.0)
    db_session.add(settings)
    db_session.add(ExamAssignment(exam_id=exam.id, student_id=student1.id))
    db_session.commit()

    attempt = start_attempt(db=db_session, exam_id=exam.id, current_user=student1)["attempt"]
    attempt.status = "submitted"
    db_session.commit()

    calculate_final_score(db=db_session, attempt_id=attempt.id)

    notif = (
        db_session.query(Notification)
        .filter(
            Notification.user_id == student1.id,
            Notification.notification_type == "RESULT_AVAILABLE",
        )
        .first()
    )
    assert notif is not None
    assert notif.title == "Result Available"


# ---------------------------------------------------------------------------
# 17. Recalculating Result Does Not Duplicate Notification
# ---------------------------------------------------------------------------
def test_17_recalculating_result_does_not_duplicate_notification(db_session):
    student1 = db_session.query(User).filter(User.email == "notif_student1@example.com").first()
    admin = db_session.query(User).filter(User.email == "notif_admin@example.com").first()

    exam = Exam(title="Result Recalc Exam", created_by=admin.id, status="published")
    db_session.add(exam)
    db_session.flush()
    settings = ExamSettings(exam_id=exam.id, duration_minutes=60, total_marks=50.0, passing_percentage=40.0)
    db_session.add(settings)
    db_session.add(ExamAssignment(exam_id=exam.id, student_id=student1.id))
    db_session.commit()

    attempt = start_attempt(db=db_session, exam_id=exam.id, current_user=student1)["attempt"]
    attempt.status = "submitted"
    db_session.commit()

    calculate_final_score(db=db_session, attempt_id=attempt.id)
    calculate_final_score(db=db_session, attempt_id=attempt.id)

    notif_count = (
        db_session.query(Notification)
        .filter(
            Notification.user_id == student1.id,
            Notification.notification_type == "RESULT_AVAILABLE",
            Notification.event_key == f"result_attempt_{attempt.id}",
        )
        .count()
    )
    assert notif_count == 1


# ---------------------------------------------------------------------------
# 18. Ranking Generation Generates Notification
# ---------------------------------------------------------------------------
def test_18_ranking_generation_generates_notification(db_session):
    student1 = db_session.query(User).filter(User.email == "notif_student1@example.com").first()
    admin = db_session.query(User).filter(User.email == "notif_admin@example.com").first()

    exam = Exam(title="Ranking Notif Exam", created_by=admin.id, status="published")
    db_session.add(exam)
    db_session.flush()
    settings = ExamSettings(exam_id=exam.id, duration_minutes=60, total_marks=100.0, passing_percentage=40.0)
    db_session.add(settings)
    db_session.add(ExamAssignment(exam_id=exam.id, student_id=student1.id))
    db_session.commit()

    attempt = start_attempt(db=db_session, exam_id=exam.id, current_user=student1)["attempt"]
    attempt.status = "submitted"
    db_session.commit()

    calculate_final_score(db=db_session, attempt_id=attempt.id)
    compute_rankings_for_exam(exam_id=exam.id, db=db_session)

    notif = (
        db_session.query(Notification)
        .filter(
            Notification.user_id == student1.id,
            Notification.notification_type == "RANKING_AVAILABLE",
        )
        .first()
    )
    assert notif is not None
    assert notif.title == "Ranking Available"


# ---------------------------------------------------------------------------
# 19. Security Monitoring Repeated Login Generates Security Alert
# ---------------------------------------------------------------------------
def test_19_security_monitoring_repeated_login_generates_alert(db_session):
    student1 = db_session.query(User).filter(User.email == "notif_student1@example.com").first()

    # Track 3 failed logins for student 1
    for _ in range(3):
        track_failed_login(
            db=db_session,
            email=student1.email,
            ip_address="127.0.0.1",
            user_agent="Pytest-Security-Client",
            status_code=401,
        )

    notif = (
        db_session.query(Notification)
        .filter(
            Notification.user_id == student1.id,
            Notification.notification_type == "SECURITY_ALERT",
        )
        .first()
    )
    assert notif is not None
    assert notif.title == "Security Alert"


# ---------------------------------------------------------------------------
# 20. Future Provider Hooks
# ---------------------------------------------------------------------------
def test_20_future_provider_hook_dispatcher(db_session):
    student1 = db_session.query(User).filter(User.email == "notif_student1@example.com").first()

    dispatched_notifications = []

    class MockEmailProvider(BaseNotificationProvider):
        def send(self, notification: Notification) -> bool:
            dispatched_notifications.append(notification)
            return True

    mock_provider = MockEmailProvider()
    dispatcher.register_provider(mock_provider)

    notif = create_notification(
        db=db_session,
        user_id=student1.id,
        title="Email Provider Hook Test",
        message="Testing provider extension hook",
        notification_type="SYSTEM",
    )

    assert notif in dispatched_notifications
