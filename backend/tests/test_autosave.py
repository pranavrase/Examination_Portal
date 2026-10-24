import pytest
from datetime import datetime, timezone, timedelta

from app.models.user import User
from app.models.role import Role
from app.models.exam import Exam, ExamSettings, ExamAssignment
from app.models.question import QuestionCategory, Question, McqOption, CodingQuestion, CodingTestCase, ExamQuestion
from app.models.attempt import ExamAttempt, AttemptAnswer, CodingSubmission, ExecutionResult
from app.core.security import hash_password, create_access_token
from app.services.role_service import seed_default_roles


@pytest.fixture(autouse=True)
def setup_autosave_fixtures(db_session):
    """Seed default roles, users, categories, exam, questions, and attempt."""
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
    cat = QuestionCategory(name="Core", topic="General", difficulty="medium")
    db_session.add(cat)
    db_session.flush()

    # Exam (Active, 60 minutes duration)
    exam = Exam(
        title="Full Assessment Exam",
        description="MCQ + Coding combined exam",
        created_by=examiner.id,
        status="published",
    )
    db_session.add(exam)
    db_session.flush()

    settings = ExamSettings(
        exam_id=exam.id,
        duration_minutes=60,
        total_marks=100.0,
        passing_percentage=40.0,
        negative_marking_ratio=0.25,
    )
    db_session.add(settings)

    # Exam Assignment for Student 1
    assign1 = ExamAssignment(
        exam_id=exam.id,
        student_id=student1.id,
        assigned_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    db_session.add(assign1)

    # MCQ Question 1 (part of exam)
    q_mcq1 = Question(
        category_id=cat.id,
        question_type="mcq",
        question_text="What is Python?",
        marks=5.0,
        created_by=examiner.id,
    )
    db_session.add(q_mcq1)
    db_session.flush()

    opt1_a = McqOption(question_id=q_mcq1.id, option_text="A snake", is_correct=False)
    opt1_b = McqOption(question_id=q_mcq1.id, option_text="A programming language", is_correct=True)
    db_session.add_all([opt1_a, opt1_b])

    eq_mcq1 = ExamQuestion(exam_id=exam.id, question_id=q_mcq1.id, question_order=1)
    db_session.add(eq_mcq1)

    # MCQ Question 2 (part of exam)
    q_mcq2 = Question(
        category_id=cat.id,
        question_type="mcq",
        question_text="What is 2 + 2?",
        marks=5.0,
        created_by=examiner.id,
    )
    db_session.add(q_mcq2)
    db_session.flush()

    opt2_a = McqOption(question_id=q_mcq2.id, option_text="3", is_correct=False)
    opt2_b = McqOption(question_id=q_mcq2.id, option_text="4", is_correct=True)
    db_session.add_all([opt2_a, opt2_b])

    eq_mcq2 = ExamQuestion(exam_id=exam.id, question_id=q_mcq2.id, question_order=2)
    db_session.add(eq_mcq2)

    # MCQ Question 3 (NOT part of exam)
    q_unrelated = Question(
        category_id=cat.id,
        question_type="mcq",
        question_text="Unrelated Question?",
        marks=5.0,
        created_by=examiner.id,
    )
    db_session.add(q_unrelated)
    db_session.flush()

    opt_unrelated = McqOption(question_id=q_unrelated.id, option_text="Nope", is_correct=False)
    db_session.add(opt_unrelated)

    # Coding Question (part of exam)
    q_code = Question(
        category_id=cat.id,
        question_type="coding",
        question_text="Write a function to return 42",
        marks=20.0,
        created_by=examiner.id,
    )
    db_session.add(q_code)
    db_session.flush()

    cq = CodingQuestion(
        question_id=q_code.id,
        problem_statement="Return the number 42",
        allowed_languages=["python", "javascript", "cpp"],
        time_limit_ms=2000,
        memory_limit_kb=128000,
    )
    db_session.add(cq)
    db_session.flush()

    tc1 = CodingTestCase(coding_question_id=cq.id, input="", expected_output="42", is_sample=True, is_hidden=False)
    db_session.add(tc1)

    eq_code = ExamQuestion(exam_id=exam.id, question_id=q_code.id, question_order=3)
    db_session.add(eq_code)

    # Student 1 Active Attempt
    attempt1 = ExamAttempt(
        exam_id=exam.id,
        student_id=student1.id,
        status="in_progress",
        started_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    db_session.add(attempt1)

    # Student 2 Active Attempt
    attempt2 = ExamAttempt(
        exam_id=exam.id,
        student_id=student2.id,
        status="in_progress",
        started_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    db_session.add(attempt2)

    db_session.commit()


def get_auth_header(user_id: int, email: str, role: str) -> dict:
    token = create_access_token(user_id=user_id, email=email, role=role)
    return {"Authorization": f"Bearer {token}"}


# ==============================================================================
# 1. AUTHENTICATION & AUTHORIZATION TESTS
# ==============================================================================

def test_unauthenticated_request_is_rejected(client, db_session):
    attempt = db_session.query(ExamAttempt).first()
    res = client.put(f"/exam-attempts/{attempt.id}/answers/autosave", json={"question_id": 1, "selected_option_id": 1})
    assert res.status_code == 401


def test_examiner_or_admin_is_rejected_from_autosave(client, db_session):
    examiner = db_session.query(User).filter(User.email == "examiner@example.com").first()
    headers = get_auth_header(examiner.id, examiner.email, "examiner")
    attempt = db_session.query(ExamAttempt).first()

    res = client.put(
        f"/exam-attempts/{attempt.id}/answers/autosave",
        json={"question_id": 1, "selected_option_id": 1},
        headers=headers,
    )
    assert res.status_code == 403
    assert "Operation restricted to users with roles: student" in res.json()["detail"]


def test_student_cannot_autosave_another_students_attempt(client, db_session):
    student1 = db_session.query(User).filter(User.email == "student1@example.com").first()
    student2 = db_session.query(User).filter(User.email == "student2@example.com").first()
    headers1 = get_auth_header(student1.id, student1.email, "student")
    attempt2 = db_session.query(ExamAttempt).filter(ExamAttempt.student_id == student2.id).first()

    # Student 1 attempts to autosave attempt 2
    res = client.put(
        f"/exam-attempts/{attempt2.id}/answers/autosave",
        json={"question_id": 1, "selected_option_id": 1},
        headers=headers1,
    )
    assert res.status_code == 403
    assert "You are not authorized to modify this attempt" in res.json()["detail"]


# ==============================================================================
# 2. MCQ AUTOSAVE TESTS
# ==============================================================================

def test_mcq_autosave_creates_new_answer(client, db_session):
    student1 = db_session.query(User).filter(User.email == "student1@example.com").first()
    headers = get_auth_header(student1.id, student1.email, "student")
    attempt = db_session.query(ExamAttempt).filter(ExamAttempt.student_id == student1.id).first()
    q1 = db_session.query(Question).filter(Question.question_text == "What is Python?").first()
    opt_b = db_session.query(McqOption).filter(McqOption.question_id == q1.id, McqOption.option_text == "A programming language").first()

    res = client.put(
        f"/exam-attempts/{attempt.id}/answers/autosave",
        json={"question_id": q1.id, "selected_option_id": opt_b.id},
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["attempt_id"] == attempt.id
    assert data["question_id"] == q1.id
    assert data["selected_option_id"] == opt_b.id

    # Verify DB record
    ans = db_session.query(AttemptAnswer).filter(
        AttemptAnswer.attempt_id == attempt.id,
        AttemptAnswer.question_id == q1.id,
    ).first()
    assert ans is not None
    assert ans.selected_option_id == opt_b.id
    # Ensure marks are not finalized / scored during autosave
    assert ans.is_correct is None
    assert ans.marks_awarded is None


def test_mcq_autosave_updates_existing_answer_without_duplication(client, db_session):
    student1 = db_session.query(User).filter(User.email == "student1@example.com").first()
    headers = get_auth_header(student1.id, student1.email, "student")
    attempt = db_session.query(ExamAttempt).filter(ExamAttempt.student_id == student1.id).first()
    q1 = db_session.query(Question).filter(Question.question_text == "What is Python?").first()
    opt_a = db_session.query(McqOption).filter(McqOption.question_id == q1.id, McqOption.option_text == "A snake").first()
    opt_b = db_session.query(McqOption).filter(McqOption.question_id == q1.id, McqOption.option_text == "A programming language").first()

    # First save option A
    client.put(
        f"/exam-attempts/{attempt.id}/answers/autosave",
        json={"question_id": q1.id, "selected_option_id": opt_a.id},
        headers=headers,
    )

    # Second save updates to option B
    res = client.put(
        f"/exam-attempts/{attempt.id}/answers/autosave",
        json={"question_id": q1.id, "selected_option_id": opt_b.id},
        headers=headers,
    )
    assert res.status_code == 200

    # Ensure EXACTLY ONE AttemptAnswer row exists
    rows = db_session.query(AttemptAnswer).filter(
        AttemptAnswer.attempt_id == attempt.id,
        AttemptAnswer.question_id == q1.id,
    ).all()
    assert len(rows) == 1
    assert rows[0].selected_option_id == opt_b.id


def test_mcq_autosave_allows_clearing_selected_option(client, db_session):
    student1 = db_session.query(User).filter(User.email == "student1@example.com").first()
    headers = get_auth_header(student1.id, student1.email, "student")
    attempt = db_session.query(ExamAttempt).filter(ExamAttempt.student_id == student1.id).first()
    q1 = db_session.query(Question).filter(Question.question_text == "What is Python?").first()
    opt_b = db_session.query(McqOption).filter(McqOption.question_id == q1.id, McqOption.option_text == "A programming language").first()

    # Save initial answer
    client.put(
        f"/exam-attempts/{attempt.id}/answers/autosave",
        json={"question_id": q1.id, "selected_option_id": opt_b.id},
        headers=headers,
    )

    # Clear answer with null selected_option_id
    res = client.put(
        f"/exam-attempts/{attempt.id}/answers/autosave",
        json={"question_id": q1.id, "selected_option_id": None},
        headers=headers,
    )
    assert res.status_code == 200
    assert res.json()["selected_option_id"] is None

    ans = db_session.query(AttemptAnswer).filter(
        AttemptAnswer.attempt_id == attempt.id,
        AttemptAnswer.question_id == q1.id,
    ).first()
    assert ans.selected_option_id is None


def test_mcq_autosave_nonexistent_attempt_returns_404(client, db_session):
    student1 = db_session.query(User).filter(User.email == "student1@example.com").first()
    headers = get_auth_header(student1.id, student1.email, "student")

    res = client.put(
        "/exam-attempts/99999/answers/autosave",
        json={"question_id": 1, "selected_option_id": 1},
        headers=headers,
    )
    assert res.status_code == 404
    assert "Exam attempt not found" in res.json()["detail"]


def test_mcq_autosave_question_not_part_of_exam_returns_400(client, db_session):
    student1 = db_session.query(User).filter(User.email == "student1@example.com").first()
    headers = get_auth_header(student1.id, student1.email, "student")
    attempt = db_session.query(ExamAttempt).filter(ExamAttempt.student_id == student1.id).first()
    q_unrelated = db_session.query(Question).filter(Question.question_text == "Unrelated Question?").first()
    opt = db_session.query(McqOption).filter(McqOption.question_id == q_unrelated.id).first()

    res = client.put(
        f"/exam-attempts/{attempt.id}/answers/autosave",
        json={"question_id": q_unrelated.id, "selected_option_id": opt.id},
        headers=headers,
    )
    assert res.status_code == 400
    assert "Question does not belong to this exam" in res.json()["detail"]


def test_mcq_autosave_option_belonging_to_another_question_returns_400(client, db_session):
    student1 = db_session.query(User).filter(User.email == "student1@example.com").first()
    headers = get_auth_header(student1.id, student1.email, "student")
    attempt = db_session.query(ExamAttempt).filter(ExamAttempt.student_id == student1.id).first()
    q1 = db_session.query(Question).filter(Question.question_text == "What is Python?").first()
    q2 = db_session.query(Question).filter(Question.question_text == "What is 2 + 2?").first()
    opt2_b = db_session.query(McqOption).filter(McqOption.question_id == q2.id).first()

    # Pass option of Q2 for Q1
    res = client.put(
        f"/exam-attempts/{attempt.id}/answers/autosave",
        json={"question_id": q1.id, "selected_option_id": opt2_b.id},
        headers=headers,
    )
    assert res.status_code == 400
    assert "Selected option does not belong to this question" in res.json()["detail"]


def test_mcq_autosave_submitted_attempt_is_rejected(client, db_session):
    student1 = db_session.query(User).filter(User.email == "student1@example.com").first()
    headers = get_auth_header(student1.id, student1.email, "student")
    attempt = db_session.query(ExamAttempt).filter(ExamAttempt.student_id == student1.id).first()
    attempt.status = "submitted"
    attempt.submitted_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db_session.commit()

    q1 = db_session.query(Question).filter(Question.question_text == "What is Python?").first()
    opt1 = db_session.query(McqOption).filter(McqOption.question_id == q1.id).first()

    res = client.put(
        f"/exam-attempts/{attempt.id}/answers/autosave",
        json={"question_id": q1.id, "selected_option_id": opt1.id},
        headers=headers,
    )
    assert res.status_code == 400
    assert "Exam attempt is no longer active" in res.json()["detail"]


def test_mcq_autosave_expired_attempt_is_rejected(client, db_session):
    student1 = db_session.query(User).filter(User.email == "student1@example.com").first()
    headers = get_auth_header(student1.id, student1.email, "student")
    attempt = db_session.query(ExamAttempt).filter(ExamAttempt.student_id == student1.id).first()
    # Started 3 hours ago for a 60 min exam
    attempt.started_at = (datetime.now(timezone.utc) - timedelta(hours=3)).replace(tzinfo=None)
    db_session.commit()

    q1 = db_session.query(Question).filter(Question.question_text == "What is Python?").first()
    opt1 = db_session.query(McqOption).filter(McqOption.question_id == q1.id).first()

    res = client.put(
        f"/exam-attempts/{attempt.id}/answers/autosave",
        json={"question_id": q1.id, "selected_option_id": opt1.id},
        headers=headers,
    )
    assert res.status_code == 400
    assert "Exam time has expired" in res.json()["detail"]


# ==============================================================================
# 3. CODING DRAFT AUTOSAVE TESTS
# ==============================================================================

def test_coding_draft_autosave_creates_draft(client, db_session):
    student1 = db_session.query(User).filter(User.email == "student1@example.com").first()
    headers = get_auth_header(student1.id, student1.email, "student")
    attempt = db_session.query(ExamAttempt).filter(ExamAttempt.student_id == student1.id).first()
    cq = db_session.query(CodingQuestion).first()

    res = client.put(
        f"/exam-attempts/{attempt.id}/coding/{cq.id}/autosave",
        json={"language": "python", "source_code": "def solution():\n    return 42"},
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["attempt_id"] == attempt.id
    assert data["coding_question_id"] == cq.id
    assert data["language"] == "python"

    # Verify DB record
    draft = db_session.query(CodingSubmission).filter(
        CodingSubmission.attempt_id == attempt.id,
        CodingSubmission.coding_question_id == cq.id,
    ).first()
    assert draft is not None
    assert draft.is_final is False
    assert draft.status == "draft"
    assert draft.source_code == "def solution():\n    return 42"
    # Ensure no ExecutionResults were created (no code execution during autosave)
    exec_results = db_session.query(ExecutionResult).filter(ExecutionResult.submission_id == draft.id).all()
    assert len(exec_results) == 0


def test_coding_draft_autosave_by_question_id(client, db_session):
    """Verify that using Question.id instead of CodingQuestion.id also resolves correctly."""
    student1 = db_session.query(User).filter(User.email == "student1@example.com").first()
    headers = get_auth_header(student1.id, student1.email, "student")
    attempt = db_session.query(ExamAttempt).filter(ExamAttempt.student_id == student1.id).first()
    q_code = db_session.query(Question).filter(Question.question_type == "coding").first()

    res = client.put(
        f"/exam-attempts/{attempt.id}/coding/{q_code.id}/autosave",
        json={"language": "python", "source_code": "print('hello')"},
        headers=headers,
    )
    assert res.status_code == 200
    assert res.json()["success"] is True


def test_coding_draft_autosave_updates_existing_draft_without_duplication(client, db_session):
    student1 = db_session.query(User).filter(User.email == "student1@example.com").first()
    headers = get_auth_header(student1.id, student1.email, "student")
    attempt = db_session.query(ExamAttempt).filter(ExamAttempt.student_id == student1.id).first()
    cq = db_session.query(CodingQuestion).first()

    # First autosave
    client.put(
        f"/exam-attempts/{attempt.id}/coding/{cq.id}/autosave",
        json={"language": "python", "source_code": "code v1"},
        headers=headers,
    )

    # Second autosave (updated draft)
    res = client.put(
        f"/exam-attempts/{attempt.id}/coding/{cq.id}/autosave",
        json={"language": "python", "source_code": "code v2"},
        headers=headers,
    )
    assert res.status_code == 200

    # Ensure only ONE draft record exists
    drafts = db_session.query(CodingSubmission).filter(
        CodingSubmission.attempt_id == attempt.id,
        CodingSubmission.coding_question_id == cq.id,
        CodingSubmission.is_final == False,
    ).all()
    assert len(drafts) == 1
    assert drafts[0].source_code == "code v2"


def test_coding_draft_autosave_does_not_modify_final_submission(client, db_session):
    student1 = db_session.query(User).filter(User.email == "student1@example.com").first()
    headers = get_auth_header(student1.id, student1.email, "student")
    attempt = db_session.query(ExamAttempt).filter(ExamAttempt.student_id == student1.id).first()
    cq = db_session.query(CodingQuestion).first()

    # Create an existing final submission
    final_sub = CodingSubmission(
        attempt_id=attempt.id,
        coding_question_id=cq.id,
        language="python",
        source_code="final code submission",
        status="accepted",
        score=20.0,
        is_final=True,
    )
    db_session.add(final_sub)
    db_session.commit()
    db_session.refresh(final_sub)
    final_id = final_sub.id

    # Now autosave a new draft
    res = client.put(
        f"/exam-attempts/{attempt.id}/coding/{cq.id}/autosave",
        json={"language": "python", "source_code": "new draft after final"},
        headers=headers,
    )
    assert res.status_code == 200

    # Verify final submission was untouched
    refreshed_final = db_session.query(CodingSubmission).filter(CodingSubmission.id == final_id).first()
    assert refreshed_final.source_code == "final code submission"
    assert refreshed_final.is_final is True
    assert refreshed_final.status == "accepted"

    # Verify separate draft exists
    draft = db_session.query(CodingSubmission).filter(
        CodingSubmission.attempt_id == attempt.id,
        CodingSubmission.coding_question_id == cq.id,
        CodingSubmission.is_final == False,
    ).first()
    assert draft is not None
    assert draft.source_code == "new draft after final"


def test_coding_draft_autosave_unsupported_language_returns_400(client, db_session):
    student1 = db_session.query(User).filter(User.email == "student1@example.com").first()
    headers = get_auth_header(student1.id, student1.email, "student")
    attempt = db_session.query(ExamAttempt).filter(ExamAttempt.student_id == student1.id).first()
    cq = db_session.query(CodingQuestion).first()

    res = client.put(
        f"/exam-attempts/{attempt.id}/coding/{cq.id}/autosave",
        json={"language": "rust", "source_code": "fn main() {}"},
        headers=headers,
    )
    assert res.status_code == 400
    assert "Coding language is not allowed for this question" in res.json()["detail"]


def test_coding_draft_autosave_question_not_in_exam_returns_400(client, db_session):
    student1 = db_session.query(User).filter(User.email == "student1@example.com").first()
    headers = get_auth_header(student1.id, student1.email, "student")
    attempt = db_session.query(ExamAttempt).filter(ExamAttempt.student_id == student1.id).first()
    cat = db_session.query(QuestionCategory).first()
    examiner = db_session.query(User).filter(User.email == "examiner@example.com").first()

    # Create unmapped coding question
    q_unmapped = Question(
        category_id=cat.id,
        question_type="coding",
        question_text="Unmapped coding question",
        marks=10.0,
        created_by=examiner.id,
    )
    db_session.add(q_unmapped)
    db_session.flush()

    cq_unmapped = CodingQuestion(
        question_id=q_unmapped.id,
        problem_statement="Unmapped problem",
        allowed_languages=["python"],
    )
    db_session.add(cq_unmapped)
    db_session.commit()

    res = client.put(
        f"/exam-attempts/{attempt.id}/coding/{cq_unmapped.id}/autosave",
        json={"language": "python", "source_code": "x = 1"},
        headers=headers,
    )
    assert res.status_code == 400
    assert "Question does not belong to this exam" in res.json()["detail"]


# ==============================================================================
# 4. BATCH AUTOSAVE TESTS (FRONTEND HOOK COMPATIBILITY)
# ==============================================================================

def test_batch_autosave_payload_compatibility(client, db_session):
    """
    Test the exact payload sent by frontend useAutoSave hook:
    {
      mcq_answers: { [q1.id]: opt1_b.id, [q2.id]: opt2_b.id },
      coding_drafts: { [cq.id]: { language: 'python', code: 'def solution(): pass' } }
    }
    """
    student1 = db_session.query(User).filter(User.email == "student1@example.com").first()
    headers = get_auth_header(student1.id, student1.email, "student")
    attempt = db_session.query(ExamAttempt).filter(ExamAttempt.student_id == student1.id).first()

    q1 = db_session.query(Question).filter(Question.question_text == "What is Python?").first()
    opt1_b = db_session.query(McqOption).filter(McqOption.question_id == q1.id, McqOption.option_text == "A programming language").first()

    q2 = db_session.query(Question).filter(Question.question_text == "What is 2 + 2?").first()
    opt2_b = db_session.query(McqOption).filter(McqOption.question_id == q2.id, McqOption.option_text == "4").first()

    cq = db_session.query(CodingQuestion).first()

    payload = {
        "mcq_answers": {
            str(q1.id): opt1_b.id,
            str(q2.id): opt2_b.id,
        },
        "coding_drafts": {
            str(cq.id): {
                "language": "python",
                "code": "def solution():\n    return 42",
            }
        },
    }

    res = client.put(
        f"/exam-attempts/{attempt.id}/answers/autosave",
        json=payload,
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["saved_mcq_count"] == 2
    assert data["saved_coding_draft_count"] == 1

    # Verify database state
    ans1 = db_session.query(AttemptAnswer).filter(
        AttemptAnswer.attempt_id == attempt.id,
        AttemptAnswer.question_id == q1.id,
    ).first()
    assert ans1.selected_option_id == opt1_b.id

    ans2 = db_session.query(AttemptAnswer).filter(
        AttemptAnswer.attempt_id == attempt.id,
        AttemptAnswer.question_id == q2.id,
    ).first()
    assert ans2.selected_option_id == opt2_b.id

    draft = db_session.query(CodingSubmission).filter(
        CodingSubmission.attempt_id == attempt.id,
        CodingSubmission.coding_question_id == cq.id,
    ).first()
    assert draft is not None
    assert draft.is_final is False
    assert draft.status == "draft"
    assert "def solution():" in draft.source_code
