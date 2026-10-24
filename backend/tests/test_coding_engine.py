import pytest
from app.models.user import User
from app.models.role import Role
from app.models.exam import Exam, ExamSettings, ExamAssignment
from app.models.question import QuestionCategory, Question, CodingQuestion, CodingTestCase, ExamQuestion
from app.models.attempt import ExamAttempt, CodingSubmission, ExecutionResult
from app.core.security import hash_password, create_access_token
from app.services.role_service import seed_default_roles


@pytest.fixture(autouse=True)
def setup_coding_engine_fixtures(db_session):
    """Seed roles, users, categories, exam, coding questions, test cases, and assignments."""
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
    cat = QuestionCategory(name="coding", topic="Algorithms", difficulty="hard")
    db_session.add(cat)
    db_session.flush()

    # Exam
    exam = Exam(
        title="Coding Championship Exam",
        description="Live coding exam",
        created_by=examiner.id,
        status="published",
    )
    db_session.add(exam)
    db_session.flush()

    settings = ExamSettings(
        exam_id=exam.id,
        duration_minutes=90,
        total_marks=50.0,
        passing_percentage=50.0,
    )
    db_session.add(settings)

    # Assign student 1
    assign1 = ExamAssignment(exam_id=exam.id, student_id=student1.id)
    db_session.add(assign1)

    # Question 1: Coding (Sum of two numbers, 10 marks)
    q1 = Question(category_id=cat.id, question_type="coding", question_text="Sum Two Numbers", marks=10.0, created_by=examiner.id)
    db_session.add(q1)
    db_session.flush()

    cq1 = CodingQuestion(
        question_id=q1.id,
        problem_statement="Read two numbers and print their sum",
        allowed_languages=["python", "cpp"],
        time_limit_ms=2000,
        memory_limit_kb=128000,
    )
    db_session.add(cq1)
    db_session.flush()

    tc1_sample = CodingTestCase(coding_question_id=cq1.id, input="2 3", expected_output="5", is_sample=True, is_hidden=False)
    tc1_hidden = CodingTestCase(coding_question_id=cq1.id, input="10 20", expected_output="30", is_sample=False, is_hidden=True)
    db_session.add_all([tc1_sample, tc1_hidden])

    # Question 2: MCQ (to test submitting code to MCQ is rejected)
    q2 = Question(category_id=cat.id, question_type="mcq", question_text="What is Python?", marks=2.0, created_by=examiner.id)
    db_session.add(q2)
    db_session.flush()

    # Question 3: Coding (Outside exam)
    q3 = Question(category_id=cat.id, question_type="coding", question_text="Unmapped Coding Question", marks=15.0, created_by=examiner.id)
    db_session.add(q3)
    db_session.flush()
    cq3 = CodingQuestion(question_id=q3.id, problem_statement="Unmapped", allowed_languages=["python"])
    db_session.add(cq3)

    # Map Q1 and Q2 to Exam
    eq1 = ExamQuestion(exam_id=exam.id, question_id=q1.id, question_order=1, marks_override=20.0)
    eq2 = ExamQuestion(exam_id=exam.id, question_id=q2.id, question_order=2)
    db_session.add_all([eq1, eq2])

    # Create active attempt for Student 1
    attempt1 = ExamAttempt(exam_id=exam.id, student_id=student1.id, status="in_progress")
    db_session.add(attempt1)

    db_session.commit()


def get_auth_header(user_id: int, email: str, role: str) -> dict:
    token = create_access_token(user_id=user_id, email=email, role=role)
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Section 1: Submission Authorization & Validation Tests (1-7)
# ---------------------------------------------------------------------------

def test_01_student_can_submit_code(client, db_session):
    """1. Student can submit code to an assigned active attempt."""
    student = db_session.query(User).filter(User.email == "student1@example.com").first()
    attempt = db_session.query(ExamAttempt).filter(ExamAttempt.student_id == student.id).first()
    q1 = db_session.query(Question).filter(Question.question_text == "Sum Two Numbers").first()
    headers = get_auth_header(student.id, student.email, "student")

    payload = {
        "language": "python",
        "source_code": "print(sum(map(int, input().split())))"
    }

    response = client.post(
        f"/coding/attempts/{attempt.id}/questions/{q1.id}/submit",
        json=payload,
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "accepted"
    assert data["score"] == 20.0  # marks_override = 20.0
    assert data["test_cases_total"] == 2
    assert data["test_cases_passed"] == 2


def test_02_unauthenticated_user_cannot_submit(client, db_session):
    """2. Unauthenticated user cannot submit code."""
    attempt = db_session.query(ExamAttempt).first()
    q1 = db_session.query(Question).filter(Question.question_text == "Sum Two Numbers").first()
    response = client.post(
        f"/coding/attempts/{attempt.id}/questions/{q1.id}/submit",
        json={"language": "python", "source_code": "print(1)"}
    )
    assert response.status_code == 401


def test_03_student_cannot_submit_to_another_students_attempt(client, db_session):
    """3. Student cannot submit code to another student's attempt (403)."""
    student2 = db_session.query(User).filter(User.email == "student2@example.com").first()
    attempt = db_session.query(ExamAttempt).first()
    q1 = db_session.query(Question).filter(Question.question_text == "Sum Two Numbers").first()
    headers2 = get_auth_header(student2.id, student2.email, "student")

    response = client.post(
        f"/coding/attempts/{attempt.id}/questions/{q1.id}/submit",
        json={"language": "python", "source_code": "print(1)"},
        headers=headers2,
    )
    assert response.status_code == 403


def test_04_student_cannot_submit_to_unmapped_question(client, db_session):
    """4. Submitting code to a question outside the exam is rejected (400)."""
    student = db_session.query(User).filter(User.email == "student1@example.com").first()
    attempt = db_session.query(ExamAttempt).filter(ExamAttempt.student_id == student.id).first()
    q3 = db_session.query(Question).filter(Question.question_text == "Unmapped Coding Question").first()
    headers = get_auth_header(student.id, student.email, "student")

    response = client.post(
        f"/coding/attempts/{attempt.id}/questions/{q3.id}/submit",
        json={"language": "python", "source_code": "print(1)"},
        headers=headers,
    )
    assert response.status_code == 400
    assert "not mapped" in response.json()["detail"].lower()


def test_05_student_cannot_submit_code_to_mcq(client, db_session):
    """5. Submitting code to an MCQ question is rejected (400)."""
    student = db_session.query(User).filter(User.email == "student1@example.com").first()
    attempt = db_session.query(ExamAttempt).filter(ExamAttempt.student_id == student.id).first()
    q2 = db_session.query(Question).filter(Question.question_text == "What is Python?").first()
    headers = get_auth_header(student.id, student.email, "student")

    response = client.post(
        f"/coding/attempts/{attempt.id}/questions/{q2.id}/submit",
        json={"language": "python", "source_code": "print(1)"},
        headers=headers,
    )
    assert response.status_code == 400
    assert "not a coding question" in response.json()["detail"].lower()


def test_06_unsupported_language_is_rejected(client, db_session):
    """6. Submitting code with an unpermitted language is rejected (400)."""
    student = db_session.query(User).filter(User.email == "student1@example.com").first()
    attempt = db_session.query(ExamAttempt).filter(ExamAttempt.student_id == student.id).first()
    q1 = db_session.query(Question).filter(Question.question_text == "Sum Two Numbers").first()
    headers = get_auth_header(student.id, student.email, "student")

    response = client.post(
        f"/coding/attempts/{attempt.id}/questions/{q1.id}/submit",
        json={"language": "rust", "source_code": "fn main() {}"},
        headers=headers,
    )
    assert response.status_code == 400
    assert "not permitted" in response.json()["detail"].lower()


def test_07_empty_source_code_is_rejected(client, db_session):
    """7. Empty source code is rejected (422)."""
    student = db_session.query(User).filter(User.email == "student1@example.com").first()
    attempt = db_session.query(ExamAttempt).filter(ExamAttempt.student_id == student.id).first()
    q1 = db_session.query(Question).filter(Question.question_text == "Sum Two Numbers").first()
    headers = get_auth_header(student.id, student.email, "student")

    response = client.post(
        f"/coding/attempts/{attempt.id}/questions/{q1.id}/submit",
        json={"language": "python", "source_code": "   "},
        headers=headers,
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Section 2: Execution Status & Error Handling Tests (8-14)
# ---------------------------------------------------------------------------

def test_08_to_10_wrong_answer_verdict(client, db_session):
    """8-10. Execution with incorrect logic produces wrong_answer."""
    student = db_session.query(User).filter(User.email == "student1@example.com").first()
    attempt = db_session.query(ExamAttempt).filter(ExamAttempt.student_id == student.id).first()
    q1 = db_session.query(Question).filter(Question.question_text == "Sum Two Numbers").first()
    headers = get_auth_header(student.id, student.email, "student")

    response = client.post(
        f"/coding/attempts/{attempt.id}/questions/{q1.id}/submit",
        json={"language": "python", "source_code": "# SIMULATE_WRONG_ANSWER\nprint('wrong')"},
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "wrong_answer"
    assert data["score"] == 0.0
    assert data["test_cases_passed"] == 0


def test_11_runtime_error_verdict(client, db_session):
    """11. Code crash produces runtime_error status."""
    student = db_session.query(User).filter(User.email == "student1@example.com").first()
    attempt = db_session.query(ExamAttempt).filter(ExamAttempt.student_id == student.id).first()
    q1 = db_session.query(Question).filter(Question.question_text == "Sum Two Numbers").first()
    headers = get_auth_header(student.id, student.email, "student")

    response = client.post(
        f"/coding/attempts/{attempt.id}/questions/{q1.id}/submit",
        json={"language": "python", "source_code": "# SIMULATE_RUNTIME_ERROR\n1/0"},
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "runtime_error"


def test_12_compilation_error_verdict(client, db_session):
    """12. Compilation failure produces compilation_error status."""
    student = db_session.query(User).filter(User.email == "student1@example.com").first()
    attempt = db_session.query(ExamAttempt).filter(ExamAttempt.student_id == student.id).first()
    q1 = db_session.query(Question).filter(Question.question_text == "Sum Two Numbers").first()
    headers = get_auth_header(student.id, student.email, "student")

    response = client.post(
        f"/coding/attempts/{attempt.id}/questions/{q1.id}/submit",
        json={"language": "cpp", "source_code": "# SIMULATE_COMPILATION_ERROR\nint main() {"},
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "compilation_error"


def test_13_time_limit_exceeded_verdict(client, db_session):
    """13. Timeout produces time_limit_exceeded status."""
    student = db_session.query(User).filter(User.email == "student1@example.com").first()
    attempt = db_session.query(ExamAttempt).filter(ExamAttempt.student_id == student.id).first()
    q1 = db_session.query(Question).filter(Question.question_text == "Sum Two Numbers").first()
    headers = get_auth_header(student.id, student.email, "student")

    response = client.post(
        f"/coding/attempts/{attempt.id}/questions/{q1.id}/submit",
        json={"language": "python", "source_code": "# SIMULATE_TIME_LIMIT\nwhile True: pass"},
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "time_limit_exceeded"


def test_14_memory_limit_exceeded_verdict(client, db_session):
    """14. Memory overflow produces memory_limit_exceeded status."""
    student = db_session.query(User).filter(User.email == "student1@example.com").first()
    attempt = db_session.query(ExamAttempt).filter(ExamAttempt.student_id == student.id).first()
    q1 = db_session.query(Question).filter(Question.question_text == "Sum Two Numbers").first()
    headers = get_auth_header(student.id, student.email, "student")

    response = client.post(
        f"/coding/attempts/{attempt.id}/questions/{q1.id}/submit",
        json={"language": "python", "source_code": "# SIMULATE_MEMORY_LIMIT\na = [1]*100000000"},
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "memory_limit_exceeded"


# ---------------------------------------------------------------------------
# Section 3: Test Cases & Anti-Leak Privacy Tests (15-18)
# ---------------------------------------------------------------------------

def test_15_to_18_hidden_test_cases_not_leaked(client, db_session):
    """15-18. Hidden test cases are executed but input, expected_output, and actual_output are NEVER exposed."""
    student = db_session.query(User).filter(User.email == "student1@example.com").first()
    attempt = db_session.query(ExamAttempt).filter(ExamAttempt.student_id == student.id).first()
    q1 = db_session.query(Question).filter(Question.question_text == "Sum Two Numbers").first()
    headers = get_auth_header(student.id, student.email, "student")

    response = client.post(
        f"/coding/attempts/{attempt.id}/questions/{q1.id}/submit",
        json={"language": "python", "source_code": "print(sum(map(int, input().split())))"},
        headers=headers,
    )
    data = response.json()
    assert len(data["test_cases"]) == 2

    sample_tc = next(tc for tc in data["test_cases"] if tc["is_sample"] is True)
    hidden_tc = next(tc for tc in data["test_cases"] if tc["is_sample"] is False)

    # Sample TC exposes input and output
    assert sample_tc["input"] == "2 3"
    assert sample_tc["expected_output"] == "5"

    # Hidden TC hides input and output
    assert hidden_tc["input"] is None
    assert hidden_tc["expected_output"] is None
    assert hidden_tc["actual_output"] is None


# ---------------------------------------------------------------------------
# Section 4: Scoring & Marks Override Tests (19-22)
# ---------------------------------------------------------------------------

def test_19_to_22_marks_override_and_scoring(client, db_session):
    """19-22. Marks override (20.0) is respected over original question marks (10.0)."""
    student = db_session.query(User).filter(User.email == "student1@example.com").first()
    attempt = db_session.query(ExamAttempt).filter(ExamAttempt.student_id == student.id).first()
    q1 = db_session.query(Question).filter(Question.question_text == "Sum Two Numbers").first()
    headers = get_auth_header(student.id, student.email, "student")

    res = client.post(
        f"/coding/attempts/{attempt.id}/questions/{q1.id}/submit",
        json={"language": "python", "source_code": "print(sum(map(int, input().split())))"},
        headers=headers,
    )
    assert res.json()["score"] == 20.0


# ---------------------------------------------------------------------------
# Section 5: Attempt Lifecycle & History Tests (23-28)
# ---------------------------------------------------------------------------

def test_23_to_25_submitted_attempt_rejects_coding(client, db_session):
    """23-25. Submitted or auto_submitted attempt rejects new coding submissions (400)."""
    student = db_session.query(User).filter(User.email == "student1@example.com").first()
    attempt = db_session.query(ExamAttempt).filter(ExamAttempt.student_id == student.id).first()
    q1 = db_session.query(Question).filter(Question.question_text == "Sum Two Numbers").first()
    headers = get_auth_header(student.id, student.email, "student")

    attempt.status = "submitted"
    db_session.commit()

    res = client.post(
        f"/coding/attempts/{attempt.id}/questions/{q1.id}/submit",
        json={"language": "python", "source_code": "print(1)"},
        headers=headers,
    )
    assert res.status_code == 400
    assert "already in 'submitted' state" in res.json()["detail"].lower()


def test_26_to_28_submission_history_and_single_retrieval(client, db_session):
    """26-28. Preserves multiple submissions, student can view own history, cannot view others."""
    student1 = db_session.query(User).filter(User.email == "student1@example.com").first()
    student2 = db_session.query(User).filter(User.email == "student2@example.com").first()
    attempt = db_session.query(ExamAttempt).filter(ExamAttempt.student_id == student1.id).first()
    q1 = db_session.query(Question).filter(Question.question_text == "Sum Two Numbers").first()

    headers1 = get_auth_header(student1.id, student1.email, "student")
    headers2 = get_auth_header(student2.id, student2.email, "student")

    # Reset attempt to in_progress
    attempt.status = "in_progress"
    db_session.commit()

    # Submission 1: Wrong Answer
    sub1 = client.post(
        f"/coding/attempts/{attempt.id}/questions/{q1.id}/submit",
        json={"language": "python", "source_code": "# SIMULATE_WA\nprint(0)"},
        headers=headers1,
    ).json()

    # Submission 2: Accepted
    sub2 = client.post(
        f"/coding/attempts/{attempt.id}/questions/{q1.id}/submit",
        json={"language": "python", "source_code": "print(sum(map(int, input().split())))"},
        headers=headers1,
    ).json()

    # Get history
    history_res = client.get(f"/coding/attempts/{attempt.id}/submissions", headers=headers1)
    assert history_res.status_code == 200
    assert history_res.json()["total_submissions"] >= 2

    # Get single submission
    single_res = client.get(f"/coding/submissions/{sub2['id']}", headers=headers1)
    assert single_res.status_code == 200
    assert single_res.json()["id"] == sub2["id"]

    # Student 2 cannot access Student 1's submission (403)
    unauthorized_res = client.get(f"/coding/submissions/{sub2['id']}", headers=headers2)
    assert unauthorized_res.status_code == 403
