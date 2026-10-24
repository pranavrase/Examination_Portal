import pytest
from datetime import datetime, timezone, timedelta

from app.models.user import User
from app.models.role import Role
from app.models.exam import Exam, ExamSettings, ExamAssignment
from app.models.question import QuestionCategory, Question, McqOption, CodingQuestion, CodingTestCase, ExamQuestion
from app.models.attempt import ExamAttempt, AttemptAnswer, CodingSubmission
from app.models.result import Result
from app.models.log import ActivityLog
from app.core.security import hash_password, create_access_token
from app.services.role_service import seed_default_roles
from app.services.exam_attempt_service import auto_submit_expired_attempts, process_attempt_result


@pytest.fixture(autouse=True)
def setup_exam_attempts_fixtures(db_session):
    """Seed default roles, users, categories, exams, questions, and assignments."""
    seed_default_roles(db_session)

    # 1. Admin
    admin = User(
        email="admin@example.com",
        full_name="Admin User",
        password_hash=hash_password("AdminPass123"),
        role="admin",
        is_active=True,
    )
    admin_role = db_session.query(Role).filter(Role.name == "admin").first()
    if admin_role:
        admin.roles.append(admin_role)
    db_session.add(admin)

    # 2. Examiner
    examiner = User(
        email="examiner@example.com",
        full_name="Examiner User",
        password_hash=hash_password("ExaminerPass123"),
        role="examiner",
        is_active=True,
    )
    examiner_role = db_session.query(Role).filter(Role.name == "examiner").first()
    if examiner_role:
        examiner.roles.append(examiner_role)
    db_session.add(examiner)

    # 3. Student 1
    student1 = User(
        email="student1@example.com",
        full_name="Student One",
        password_hash=hash_password("StudentPass123"),
        role="student",
        is_active=True,
    )
    student_role = db_session.query(Role).filter(Role.name == "student").first()
    if student_role:
        student1.roles.append(student_role)
    db_session.add(student1)

    # 4. Student 2
    student2 = User(
        email="student2@example.com",
        full_name="Student Two",
        password_hash=hash_password("StudentPass123"),
        role="student",
        is_active=True,
    )
    if student_role:
        student2.roles.append(student_role)
    db_session.add(student2)

    # Category
    cat = QuestionCategory(name="CS", topic="Programming", difficulty="medium")
    db_session.add(cat)
    db_session.flush()

    # Exam 1 (Published, 60 minutes, passing 50%)
    exam1 = Exam(
        title="Final CS Exam",
        description="Exam covering MCQ and Coding",
        created_by=examiner.id,
        status="published",
    )
    db_session.add(exam1)
    db_session.flush()

    settings1 = ExamSettings(
        exam_id=exam1.id,
        duration_minutes=60,
        total_marks=30.0,
        passing_percentage=50.0,
        negative_marking_ratio=0.25,
    )
    db_session.add(settings1)

    # Exam 3 (Published, 10 minutes - testing custom duration)
    exam3 = Exam(
        title="Quick Quiz",
        description="10-minute quick assessment",
        created_by=examiner.id,
        status="published",
    )
    db_session.add(exam3)
    db_session.flush()

    settings3 = ExamSettings(
        exam_id=exam3.id,
        duration_minutes=10,
        total_marks=10.0,
        passing_percentage=60.0,
        negative_marking_ratio=0.0,
    )
    db_session.add(settings3)

    # Exam 2 (Draft status - cannot be attempted)
    exam_draft = Exam(
        title="Draft Exam",
        created_by=examiner.id,
        status="draft",
    )
    db_session.add(exam_draft)
    db_session.flush()

    # Assign Student 1 to Exam 1
    assign1 = ExamAssignment(
        exam_id=exam1.id,
        student_id=student1.id,
        assigned_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    db_session.add(assign1)

    # Assign Student 1 to Exam 3 (10-minute test)
    assign3 = ExamAssignment(
        exam_id=exam3.id,
        student_id=student1.id,
        assigned_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    db_session.add(assign3)

    # Assign Student 2 to Exam Draft
    assign_draft = ExamAssignment(
        exam_id=exam_draft.id,
        student_id=student2.id,
        assigned_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    db_session.add(assign_draft)

    # Question 1: MCQ (10 marks)
    q1 = Question(
        category_id=cat.id,
        question_type="mcq",
        question_text="What is 10 * 10?",
        marks=10.0,
        created_by=examiner.id,
    )
    db_session.add(q1)
    db_session.flush()

    opt1_wrong = McqOption(question_id=q1.id, option_text="50", is_correct=False)
    opt1_correct = McqOption(question_id=q1.id, option_text="100", is_correct=True)
    db_session.add_all([opt1_wrong, opt1_correct])

    eq1 = ExamQuestion(exam_id=exam1.id, question_id=q1.id, question_order=1)
    db_session.add(eq1)

    # Question 2: Coding (20 marks)
    q2 = Question(
        category_id=cat.id,
        question_type="coding",
        question_text="Print Hello",
        marks=20.0,
        created_by=examiner.id,
    )
    db_session.add(q2)
    db_session.flush()

    cq = CodingQuestion(
        question_id=q2.id,
        problem_statement="Print Hello",
        allowed_languages=["python"],
        time_limit_ms=2000,
        memory_limit_kb=128000,
    )
    db_session.add(cq)

    eq2 = ExamQuestion(exam_id=exam1.id, question_id=q2.id, question_order=2)
    db_session.add(eq2)

    db_session.commit()


def get_auth_header(user_id: int, email: str, role: str) -> dict:
    token = create_access_token(user_id=user_id, email=email, role=role)
    return {"Authorization": f"Bearer {token}"}


# ==============================================================================
# 1. START ATTEMPT TESTS
# ==============================================================================

def test_student_can_start_assigned_exam(client, db_session):
    student1 = db_session.query(User).filter(User.email == "student1@example.com").first()
    exam1 = db_session.query(Exam).filter(Exam.title == "Final CS Exam").first()
    headers = get_auth_header(student1.id, student1.email, "student")

    res = client.post(f"/exams/{exam1.id}/attempt", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["exam_id"] == exam1.id
    assert data["status"] == "in_progress"
    assert data["duration_minutes"] == 60
    assert data["remaining_seconds"] == 3600
    assert "attempt_id" in data

    # Verify DB attempt record
    att = db_session.query(ExamAttempt).filter(ExamAttempt.id == data["attempt_id"]).first()
    assert att is not None
    assert att.student_id == student1.id
    assert att.status == "in_progress"
    assert att.started_at is not None


def test_start_attempt_alias_path(client, db_session):
    student1 = db_session.query(User).filter(User.email == "student1@example.com").first()
    exam1 = db_session.query(Exam).filter(Exam.title == "Final CS Exam").first()
    headers = get_auth_header(student1.id, student1.email, "student")

    res = client.post(f"/exam-attempts/exams/{exam1.id}/attempt", headers=headers)
    assert res.status_code == 200
    assert res.json()["success"] is True


def test_unauthenticated_cannot_start_attempt(client, db_session):
    exam1 = db_session.query(Exam).filter(Exam.title == "Final CS Exam").first()
    res = client.post(f"/exams/{exam1.id}/attempt")
    assert res.status_code == 401


def test_examiner_or_admin_cannot_start_attempt(client, db_session):
    examiner = db_session.query(User).filter(User.email == "examiner@example.com").first()
    exam1 = db_session.query(Exam).filter(Exam.title == "Final CS Exam").first()
    headers = get_auth_header(examiner.id, examiner.email, "examiner")

    res = client.post(f"/exams/{exam1.id}/attempt", headers=headers)
    assert res.status_code == 403
    assert "Operation restricted to users with roles: student" in res.json()["detail"]


def test_unassigned_student_cannot_start_attempt(client, db_session):
    student2 = db_session.query(User).filter(User.email == "student2@example.com").first()
    exam1 = db_session.query(Exam).filter(Exam.title == "Final CS Exam").first()
    headers = get_auth_header(student2.id, student2.email, "student")

    res = client.post(f"/exams/{exam1.id}/attempt", headers=headers)
    assert res.status_code == 403
    assert "You are not assigned to this exam" in res.json()["detail"]


def test_student_cannot_start_draft_exam(client, db_session):
    student2 = db_session.query(User).filter(User.email == "student2@example.com").first()
    exam_draft = db_session.query(Exam).filter(Exam.title == "Draft Exam").first()
    headers = get_auth_header(student2.id, student2.email, "student")

    res = client.post(f"/exams/{exam_draft.id}/attempt", headers=headers)
    assert res.status_code == 400
    assert "Exam is not published" in res.json()["detail"]


def test_student_cannot_start_nonexistent_exam(client, db_session):
    student1 = db_session.query(User).filter(User.email == "student1@example.com").first()
    headers = get_auth_header(student1.id, student1.email, "student")

    res = client.post("/exams/99999/attempt", headers=headers)
    assert res.status_code == 404
    assert "Exam with ID 99999 not found" in res.json()["detail"]


def test_start_attempt_resumes_existing_active_attempt(client, db_session):
    student1 = db_session.query(User).filter(User.email == "student1@example.com").first()
    exam1 = db_session.query(Exam).filter(Exam.title == "Final CS Exam").first()
    headers = get_auth_header(student1.id, student1.email, "student")

    # Start first time
    res1 = client.post(f"/exams/{exam1.id}/attempt", headers=headers)
    att_id1 = res1.json()["attempt_id"]

    # Start second time (resume)
    res2 = client.post(f"/exams/{exam1.id}/attempt", headers=headers)
    assert res2.status_code == 200
    assert res2.json()["attempt_id"] == att_id1
    assert res2.json()["status"] == "in_progress"

    # Verify only 1 attempt row exists in DB
    count = db_session.query(ExamAttempt).filter(
        ExamAttempt.exam_id == exam1.id,
        ExamAttempt.student_id == student1.id,
    ).count()
    assert count == 1


def test_cannot_restart_already_submitted_exam(client, db_session):
    student1 = db_session.query(User).filter(User.email == "student1@example.com").first()
    exam1 = db_session.query(Exam).filter(Exam.title == "Final CS Exam").first()
    headers = get_auth_header(student1.id, student1.email, "student")

    # Start attempt
    res1 = client.post(f"/exams/{exam1.id}/attempt", headers=headers)
    att_id = res1.json()["attempt_id"]

    # Submit attempt
    client.post(f"/exam-attempts/{att_id}/submit", headers=headers)

    # Try starting again
    res3 = client.post(f"/exams/{exam1.id}/attempt", headers=headers)
    assert res3.status_code == 409
    assert "Exam attempt has already been submitted" in res3.json()["detail"]


# ==============================================================================
# 2. REMAINING TIME TESTS
# ==============================================================================

def test_student_can_get_remaining_time(client, db_session):
    student1 = db_session.query(User).filter(User.email == "student1@example.com").first()
    exam1 = db_session.query(Exam).filter(Exam.title == "Final CS Exam").first()
    headers = get_auth_header(student1.id, student1.email, "student")

    res = client.post(f"/exams/{exam1.id}/attempt", headers=headers)
    att_id = res.json()["attempt_id"]

    rem_res = client.get(f"/exam-attempts/{att_id}/remaining-time", headers=headers)
    assert rem_res.status_code == 200
    data = rem_res.json()
    assert data["attempt_id"] == att_id
    assert data["exam_id"] == exam1.id
    assert data["status"] == "in_progress"
    assert data["remaining_seconds"] <= 3600
    assert data["remaining_seconds"] >= 3590


def test_cannot_get_another_students_remaining_time(client, db_session):
    student1 = db_session.query(User).filter(User.email == "student1@example.com").first()
    student2 = db_session.query(User).filter(User.email == "student2@example.com").first()
    exam1 = db_session.query(Exam).filter(Exam.title == "Final CS Exam").first()

    headers1 = get_auth_header(student1.id, student1.email, "student")
    headers2 = get_auth_header(student2.id, student2.email, "student")

    res = client.post(f"/exams/{exam1.id}/attempt", headers=headers1)
    att_id = res.json()["attempt_id"]

    # Student 2 tries to access Student 1's remaining time
    res_forbidden = client.get(f"/exam-attempts/{att_id}/remaining-time", headers=headers2)
    assert res_forbidden.status_code == 403
    assert "You are not authorized to view this attempt" in res_forbidden.json()["detail"]


def test_remaining_time_on_expired_attempt_triggers_auto_submit(client, db_session):
    student1 = db_session.query(User).filter(User.email == "student1@example.com").first()
    exam1 = db_session.query(Exam).filter(Exam.title == "Final CS Exam").first()
    headers = get_auth_header(student1.id, student1.email, "student")

    res = client.post(f"/exams/{exam1.id}/attempt", headers=headers)
    att_id = res.json()["attempt_id"]

    # Age the started_at to 2 hours ago (duration is 60 mins)
    att = db_session.query(ExamAttempt).filter(ExamAttempt.id == att_id).first()
    att.started_at = (datetime.now(timezone.utc) - timedelta(hours=2)).replace(tzinfo=None)
    db_session.commit()

    rem_res = client.get(f"/exam-attempts/{att_id}/remaining-time", headers=headers)
    assert rem_res.status_code == 200
    data = rem_res.json()
    assert data["remaining_seconds"] == 0
    assert data["status"] == "expired"

    # Verify attempt in DB transitioned to auto_submitted
    db_session.refresh(att)
    assert att.status == "auto_submitted"
    assert att.submitted_at is not None


# ==============================================================================
# 3. MANUAL SUBMISSION TESTS
# ==============================================================================

def test_manual_submission_finalizes_attempt_and_scores(client, db_session):
    student1 = db_session.query(User).filter(User.email == "student1@example.com").first()
    exam1 = db_session.query(Exam).filter(Exam.title == "Final CS Exam").first()
    headers = get_auth_header(student1.id, student1.email, "student")

    # Start attempt
    res = client.post(f"/exams/{exam1.id}/attempt", headers=headers)
    att_id = res.json()["attempt_id"]

    # Answer MCQ correctly via autosave
    q1 = db_session.query(Question).filter(Question.question_text == "What is 10 * 10?").first()
    opt_correct = db_session.query(McqOption).filter(McqOption.question_id == q1.id, McqOption.option_text == "100").first()

    save_res = client.put(
        f"/exam-attempts/{att_id}/answers/autosave",
        json={"question_id": q1.id, "selected_option_id": opt_correct.id},
        headers=headers,
    )
    assert save_res.status_code == 200

    # Submit attempt
    sub_res = client.post(f"/exam-attempts/{att_id}/submit", headers=headers)
    assert sub_res.status_code == 200
    data = sub_res.json()
    assert data["success"] is True
    assert data["status"] == "submitted"
    assert data["score"] == 10.0
    assert data["total_marks"] == 30.0
    assert data["percentage"] == pytest.approx(33.33, 0.1)
    assert data["pass_fail"] is False  # 33.33% < 50% passing threshold

    # Verify attempt in DB
    att = db_session.query(ExamAttempt).filter(ExamAttempt.id == att_id).first()
    assert att.status == "submitted"
    assert att.submitted_at is not None

    # Verify Result in DB
    result = db_session.query(Result).filter(Result.attempt_id == att_id).first()
    assert result is not None
    assert float(result.total_marks_obtained) == 10.0
    assert float(result.total_marks_possible) == 30.0

    # Verify ActivityLog
    log = db_session.query(ActivityLog).filter(
        ActivityLog.user_id == student1.id,
        ActivityLog.action_type == "exam_submit",
    ).first()
    assert log is not None


def test_submitted_attempt_cannot_be_submitted_again(client, db_session):
    student1 = db_session.query(User).filter(User.email == "student1@example.com").first()
    exam1 = db_session.query(Exam).filter(Exam.title == "Final CS Exam").first()
    headers = get_auth_header(student1.id, student1.email, "student")

    res = client.post(f"/exams/{exam1.id}/attempt", headers=headers)
    att_id = res.json()["attempt_id"]

    # First submit
    client.post(f"/exam-attempts/{att_id}/submit", headers=headers)

    # Second submit
    res_second = client.post(f"/exam-attempts/{att_id}/submit", headers=headers)
    assert res_second.status_code == 409
    assert "Exam attempt has already been submitted" in res_second.json()["detail"]


def test_submitted_attempt_locks_further_autosave(client, db_session):
    student1 = db_session.query(User).filter(User.email == "student1@example.com").first()
    exam1 = db_session.query(Exam).filter(Exam.title == "Final CS Exam").first()
    headers = get_auth_header(student1.id, student1.email, "student")

    res = client.post(f"/exams/{exam1.id}/attempt", headers=headers)
    att_id = res.json()["attempt_id"]

    # Submit attempt
    client.post(f"/exam-attempts/{att_id}/submit", headers=headers)

    # Attempt to autosave after submission
    q1 = db_session.query(Question).filter(Question.question_text == "What is 10 * 10?").first()
    opt = db_session.query(McqOption).filter(McqOption.question_id == q1.id).first()

    autosave_res = client.put(
        f"/exam-attempts/{att_id}/answers/autosave",
        json={"question_id": q1.id, "selected_option_id": opt.id},
        headers=headers,
    )
    assert autosave_res.status_code == 400
    assert "Exam attempt is no longer active" in autosave_res.json()["detail"]


# ==============================================================================
# 4. AUTO-SUBMIT EXPIRED ATTEMPTS
# ==============================================================================

def test_auto_submit_expired_attempts_job(client, db_session):
    student1 = db_session.query(User).filter(User.email == "student1@example.com").first()
    exam1 = db_session.query(Exam).filter(Exam.title == "Final CS Exam").first()
    headers = get_auth_header(student1.id, student1.email, "student")

    res = client.post(f"/exams/{exam1.id}/attempt", headers=headers)
    att_id = res.json()["attempt_id"]

    # Age attempt to 90 minutes ago (exam duration is 60 minutes)
    att = db_session.query(ExamAttempt).filter(ExamAttempt.id == att_id).first()
    att.started_at = (datetime.now(timezone.utc) - timedelta(minutes=90)).replace(tzinfo=None)
    db_session.commit()

    # Trigger auto-submit service function directly
    submitted_count = auto_submit_expired_attempts(db_session)
    assert submitted_count == 1

    # Verify attempt is now auto_submitted
    db_session.refresh(att)
    assert att.status == "auto_submitted"
    assert att.remaining_seconds_snapshot == 0

    # Verify Result record was generated
    result = db_session.query(Result).filter(Result.attempt_id == att_id).first()
    assert result is not None

    # Verify running it again is idempotent (does not duplicate or re-submit)
    second_run = auto_submit_expired_attempts(db_session)
    assert second_run == 0


def test_system_auto_submit_endpoint(client, db_session):
    res = client.post("/exam-attempts/system/auto-submit")
    assert res.status_code == 200
    assert res.json()["success"] is True
    assert "expired_attempts_submitted" in res.json()


# ==============================================================================
# 5. INTEGRATION TESTS (FULL LIFECYCLE FLOWS)
# ==============================================================================

def test_end_to_end_student_lifecycle_flow(client, db_session):
    """
    Test the complete flow:
    1. Student logs in / obtains token.
    2. Student is assigned an exam.
    3. Student starts exam -> attempt created in_progress.
    4. Student checks remaining time.
    5. Student answers MCQ -> Module 2.8 autosaves answer.
    6. Student writes code -> Module 2.8 autosaves coding draft.
    7. Student submits exam manually.
    8. Attempt becomes submitted.
    9. Further autosave is locked.
    10. Scoring creates Result record.
    """
    student = db_session.query(User).filter(User.email == "student1@example.com").first()
    exam = db_session.query(Exam).filter(Exam.title == "Final CS Exam").first()
    headers = get_auth_header(student.id, student.email, "student")

    # 1. Start Exam
    start_res = client.post(f"/exams/{exam.id}/attempt", headers=headers)
    assert start_res.status_code == 200
    attempt_id = start_res.json()["attempt_id"]

    # 2. Check remaining time
    time_res = client.get(f"/exam-attempts/{attempt_id}/remaining-time", headers=headers)
    assert time_res.status_code == 200
    assert time_res.json()["remaining_seconds"] > 0

    # 3. Autosave MCQ answer (Module 2.8)
    q1 = db_session.query(Question).filter(Question.question_text == "What is 10 * 10?").first()
    opt1_correct = db_session.query(McqOption).filter(McqOption.question_id == q1.id, McqOption.option_text == "100").first()
    mcq_save = client.put(
        f"/exam-attempts/{attempt_id}/answers/autosave",
        json={"question_id": q1.id, "selected_option_id": opt1_correct.id},
        headers=headers,
    )
    assert mcq_save.status_code == 200

    # 4. Autosave Coding Draft (Module 2.8)
    cq = db_session.query(CodingQuestion).first()
    code_save = client.put(
        f"/exam-attempts/{attempt_id}/coding/{cq.id}/autosave",
        json={"language": "python", "source_code": "print('Hello World')"},
        headers=headers,
    )
    assert code_save.status_code == 200

    # 5. Submit Exam
    sub_res = client.post(f"/exam-attempts/{attempt_id}/submit", headers=headers)
    assert sub_res.status_code == 200
    assert sub_res.json()["status"] == "submitted"
    assert sub_res.json()["score"] is not None

    # 6. Verify autosave lock
    post_save = client.put(
        f"/exam-attempts/{attempt_id}/answers/autosave",
        json={"question_id": q1.id, "selected_option_id": opt1_correct.id},
        headers=headers,
    )
    assert post_save.status_code == 400

    # 7. Verify Result in DB
    result = db_session.query(Result).filter(Result.attempt_id == attempt_id).first()
    assert result is not None
    assert result.calculated_at is not None


def test_end_to_end_timer_expiry_and_auto_submit_flow(client, db_session):
    """
    Test flow:
    1. Student starts exam.
    2. Timer expires.
    3. Scheduler detects expired attempt.
    4. Attempt becomes auto_submitted.
    5. Further changes rejected.
    6. Result is persisted.
    """
    student = db_session.query(User).filter(User.email == "student1@example.com").first()
    exam = db_session.query(Exam).filter(Exam.title == "Final CS Exam").first()
    headers = get_auth_header(student.id, student.email, "student")

    # Start
    start_res = client.post(f"/exams/{exam.id}/attempt", headers=headers)
    attempt_id = start_res.json()["attempt_id"]

    # Age attempt to expire
    att = db_session.query(ExamAttempt).filter(ExamAttempt.id == attempt_id).first()
    att.started_at = (datetime.now(timezone.utc) - timedelta(hours=3)).replace(tzinfo=None)
    db_session.commit()

    # System auto-submit
    submitted = auto_submit_expired_attempts(db_session)
    assert submitted == 1

    # Check remaining time reports expired
    time_res = client.get(f"/exam-attempts/{attempt_id}/remaining-time", headers=headers)
    assert time_res.status_code == 200
    assert time_res.json()["remaining_seconds"] == 0
    assert time_res.json()["status"] in ("expired", "auto_submitted")

    # Result generated
    result = db_session.query(Result).filter(Result.attempt_id == attempt_id).first()
    assert result is not None


def test_custom_duration_exam_10_minutes(client, db_session):
    """
    Test that exams with custom durations (e.g., 10 minutes) work correctly.
    This verifies the fix for removing the 60-minute default.
    """
    student1 = db_session.query(User).filter(User.email == "student1@example.com").first()
    exam3 = db_session.query(Exam).filter(Exam.title == "Quick Quiz").first()
    headers = get_auth_header(student1.id, student1.email, "student")

    # Start the 10-minute exam
    res = client.post(f"/exams/{exam3.id}/attempt", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["exam_id"] == exam3.id
    assert data["status"] == "in_progress"
    assert data["duration_minutes"] == 10  # Should be 10, not 60
    assert data["remaining_seconds"] == 600  # Should be 600 seconds (10 * 60)

    # Check remaining time endpoint
    att_id = data["attempt_id"]
    rem_res = client.get(f"/exam-attempts/{att_id}/remaining-time", headers=headers)
    assert rem_res.status_code == 200
    rem_data = rem_res.json()
    assert rem_data["duration_minutes"] == 10
    assert rem_data["remaining_seconds"] <= 600
    assert rem_data["remaining_seconds"] >= 590


# ==============================================================================
# 5. RE-ENTRY / RETAKING PREVENTION TESTS
# ==============================================================================

def test_reentry_blocked_after_submission_returns_409_with_attempt_id(client, db_session):
    """Verifies that starting/re-entering after submission returns 409 with attempt_id and status."""
    student = db_session.query(User).filter(User.email == "student1@example.com").first()
    exam = db_session.query(Exam).filter(Exam.title == "Final CS Exam").first()
    headers = get_auth_header(student.id, student.email, "student")

    # Start attempt
    start_res = client.post(f"/exams/{exam.id}/attempt", headers=headers)
    assert start_res.status_code == 200
    attempt_id = start_res.json()["attempt_id"]

    # Submit attempt
    sub_res = client.post(f"/exam-attempts/{attempt_id}/submit", headers=headers)
    assert sub_res.status_code == 200

    # Attempt to start or re-enter via POST /exams/{id}/attempt
    retry_res = client.post(f"/exams/{exam.id}/attempt", headers=headers)
    assert retry_res.status_code == 409
    body = retry_res.json()
    assert body["attempt_id"] == attempt_id
    assert body["status"] == "submitted"
    assert "Exam attempt has already been submitted" in body["detail"]

    # Verify no new attempt was created
    attempts = db_session.query(ExamAttempt).filter(
        ExamAttempt.exam_id == exam.id,
        ExamAttempt.student_id == student.id,
    ).all()
    assert len(attempts) == 1


def test_mcq_questions_blocked_after_submission_returns_409(client, db_session):
    """Verifies that GET /mcq/exams/{id}/questions is blocked with 409 once submitted."""
    student = db_session.query(User).filter(User.email == "student2@example.com").first()
    exam = db_session.query(Exam).filter(Exam.title == "Final CS Exam").first()

    # Assign student2 to exam
    db_session.add(ExamAssignment(
        exam_id=exam.id,
        student_id=student.id,
        assigned_at=datetime.now(timezone.utc).replace(tzinfo=None),
    ))
    db_session.commit()

    headers = get_auth_header(student.id, student.email, "student")

    # Start attempt
    start_res = client.post(f"/exams/{exam.id}/attempt", headers=headers)
    assert start_res.status_code == 200
    attempt_id = start_res.json()["attempt_id"]

    # Verify questions can be retrieved while in_progress
    q_res = client.get(f"/mcq/exams/{exam.id}/questions", headers=headers)
    assert q_res.status_code == 200

    # Submit attempt
    client.post(f"/exam-attempts/{attempt_id}/submit", headers=headers)

    # Calling mcq questions now must return 409 Conflict with attempt_id and status
    blocked_res = client.get(f"/mcq/exams/{exam.id}/questions", headers=headers)
    assert blocked_res.status_code == 409
    body = blocked_res.json()
    assert body["attempt_id"] == attempt_id
    assert body["status"] == "submitted"


def test_coding_questions_blocked_after_submission_returns_409(client, db_session):
    """Verifies that GET /coding/questions/{id} is blocked with 409 once submitted."""
    student = db_session.query(User).filter(User.email == "student1@example.com").first()
    exam = db_session.query(Exam).filter(Exam.title == "Final CS Exam").first()
    headers = get_auth_header(student.id, student.email, "student")

    # Start attempt
    start_res = client.post(f"/exams/{exam.id}/attempt", headers=headers)
    assert start_res.status_code == 200
    attempt_id = start_res.json()["attempt_id"]

    # Submit attempt
    client.post(f"/exam-attempts/{attempt_id}/submit", headers=headers)

    # Calling coding questions now must return 409 Conflict with attempt_id and status
    coding_res = client.get(f"/coding/questions/{exam.id}", headers=headers)
    assert coding_res.status_code == 409
    body = coding_res.json()
    assert body["attempt_id"] == attempt_id
    assert body["status"] == "submitted"


def test_reentry_blocked_after_auto_submitted_due_to_expiry(client, db_session):
    """Verifies that an auto-submitted attempt is permanently locked and returns 409."""
    student = db_session.query(User).filter(User.email == "student2@example.com").first()
    exam = db_session.query(Exam).filter(Exam.title == "Quick Quiz").first()

    # Assign student2 to exam
    db_session.add(ExamAssignment(
        exam_id=exam.id,
        student_id=student.id,
        assigned_at=datetime.now(timezone.utc).replace(tzinfo=None),
    ))
    db_session.commit()

    headers = get_auth_header(student.id, student.email, "student")

    # Start attempt
    start_res = client.post(f"/exams/{exam.id}/attempt", headers=headers)
    assert start_res.status_code == 200
    attempt_id = start_res.json()["attempt_id"]

    # Artificially set started_at in the past
    att = db_session.query(ExamAttempt).filter(ExamAttempt.id == attempt_id).first()
    att.started_at = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=150)
    att.status = "auto_submitted"
    att.submitted_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db_session.commit()

    # Try to start or re-enter
    retry_res = client.post(f"/exams/{exam.id}/attempt", headers=headers)
    assert retry_res.status_code == 409
    body = retry_res.json()
    assert body["attempt_id"] == attempt_id
    assert body["status"] == "auto_submitted"

    # Verify mcq questions also return 409 with attempt_id and auto_submitted status
    q_res = client.get(f"/mcq/exams/{exam.id}/questions", headers=headers)
    assert q_res.status_code == 409
    q_body = q_res.json()
    assert q_body["attempt_id"] == attempt_id
    assert q_body["status"] == "auto_submitted"

    # Verify no second attempt was created
    attempts = db_session.query(ExamAttempt).filter(
        ExamAttempt.exam_id == exam.id,
        ExamAttempt.student_id == student.id,
    ).all()
    assert len(attempts) == 1

