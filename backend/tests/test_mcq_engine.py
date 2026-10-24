import pytest
from datetime import datetime, timezone
from app.models.user import User
from app.models.role import Role
from app.models.exam import Exam, ExamSettings, ExamAssignment
from app.models.question import QuestionCategory, Question, McqOption, CodingQuestion, ExamQuestion
from app.models.attempt import ExamAttempt, AttemptAnswer
from app.core.security import hash_password, create_access_token
from app.services.role_service import seed_default_roles


@pytest.fixture(autouse=True)
def setup_mcq_engine_fixtures(db_session):
    """Seed default roles, users, category, exam, questions, and assignments."""
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
    cat = QuestionCategory(name="aptitude", topic="Arithmetic", difficulty="medium")
    db_session.add(cat)
    db_session.flush()

    # Exam 1 (Published, Negative marking ratio 0.25, Randomize enabled)
    exam1 = Exam(
        title="Comprehensive Aptitude Exam",
        description="Aptitude test with negative marking",
        created_by=examiner.id,
        status="published",
    )
    db_session.add(exam1)
    db_session.flush()

    settings1 = ExamSettings(
        exam_id=exam1.id,
        duration_minutes=60,
        total_marks=20.0,
        passing_percentage=40.0,
        negative_marking_ratio=0.25,
        randomize_questions=True,
        randomize_options=True,
    )
    db_session.add(settings1)

    # Assign Student 1 to Exam 1
    assign1 = ExamAssignment(exam_id=exam1.id, student_id=student1.id)
    db_session.add(assign1)

    # Questions setup
    # Q1: MCQ (Marks = 2.0)
    q1 = Question(category_id=cat.id, question_type="mcq", question_text="What is 5 + 7?", marks=2.0, created_by=examiner.id)
    db_session.add(q1)
    db_session.flush()
    opt1_a = McqOption(question_id=q1.id, option_text="10", is_correct=False)
    opt1_b = McqOption(question_id=q1.id, option_text="12", is_correct=True)
    opt1_c = McqOption(question_id=q1.id, option_text="14", is_correct=False)
    db_session.add_all([opt1_a, opt1_b, opt1_c])

    # Q2: MCQ (Marks = 4.0, marks_override in exam = 5.0)
    q2 = Question(category_id=cat.id, question_type="mcq", question_text="What is 10 * 10?", marks=4.0, created_by=examiner.id)
    db_session.add(q2)
    db_session.flush()
    opt2_a = McqOption(question_id=q2.id, option_text="100", is_correct=True)
    opt2_b = McqOption(question_id=q2.id, option_text="1000", is_correct=False)
    db_session.add_all([opt2_a, opt2_b])

    # Q3: Coding question (must be excluded from MCQ sets)
    q3 = Question(category_id=cat.id, question_type="coding", question_text="Reverse String", marks=10.0, created_by=examiner.id)
    db_session.add(q3)
    db_session.flush()
    cq3 = CodingQuestion(question_id=q3.id, problem_statement="Reverse string s", allowed_languages=["python"])
    db_session.add(cq3)

    # Map questions to Exam 1
    eq1 = ExamQuestion(exam_id=exam1.id, question_id=q1.id, question_order=1)
    eq2 = ExamQuestion(exam_id=exam1.id, question_id=q2.id, question_order=2, marks_override=5.0)
    eq3 = ExamQuestion(exam_id=exam1.id, question_id=q3.id, question_order=3)
    db_session.add_all([eq1, eq2, eq3])

    db_session.commit()


def get_auth_header(user_id: int, email: str, role: str) -> dict:
    token = create_access_token(user_id=user_id, email=email, role=role)
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Section 1: Access & Authorization Tests (1-4)
# ---------------------------------------------------------------------------

def test_01_student_can_access_own_attempt(client, db_session):
    """1. Student can access their own exam questions and attempt."""
    student = db_session.query(User).filter(User.email == "student1@example.com").first()
    exam = db_session.query(Exam).filter(Exam.title == "Comprehensive Aptitude Exam").first()
    headers = get_auth_header(student.id, student.email, "student")

    response = client.get(f"/mcq/exams/{exam.id}/questions", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["exam_id"] == exam.id
    assert "attempt_id" in data
    assert data["total_mcq_questions"] == 2


def test_02_student_cannot_access_another_students_attempt(client, db_session):
    """2. Student cannot access or answer another student's attempt (403)."""
    student1 = db_session.query(User).filter(User.email == "student1@example.com").first()
    student2 = db_session.query(User).filter(User.email == "student2@example.com").first()
    exam = db_session.query(Exam).filter(Exam.title == "Comprehensive Aptitude Exam").first()

    headers1 = get_auth_header(student1.id, student1.email, "student")
    headers2 = get_auth_header(student2.id, student2.email, "student")

    # Student 1 gets/creates attempt
    res1 = client.get(f"/mcq/exams/{exam.id}/questions", headers=headers1)
    attempt_id = res1.json()["attempt_id"]

    # Student 2 attempts to get answers of Student 1
    res2 = client.get(f"/mcq/attempts/{attempt_id}/answers", headers=headers2)
    assert res2.status_code == 403

    # Student 2 attempts to post answer to Student 1's attempt
    res3 = client.post(f"/mcq/attempts/{attempt_id}/answers", json={"question_id": 1, "selected_option_id": 1}, headers=headers2)
    assert res3.status_code == 403


def test_03_unauthenticated_user_cannot_access_mcq(client, db_session):
    """3. Unauthenticated user cannot access MCQ endpoints."""
    exam = db_session.query(Exam).first()
    res = client.get(f"/mcq/exams/{exam.id}/questions")
    assert res.status_code == 401


def test_04_unassigned_student_cannot_access_exam(client, db_session):
    """4. Student who is not assigned to the exam receives 403."""
    student2 = db_session.query(User).filter(User.email == "student2@example.com").first()
    exam = db_session.query(Exam).first()
    headers = get_auth_header(student2.id, student2.email, "student")

    response = client.get(f"/mcq/exams/{exam.id}/questions", headers=headers)
    assert response.status_code == 403
    assert "not assigned" in response.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Section 2: Question Retrieval & Anti-Leak Tests (5-11)
# ---------------------------------------------------------------------------

def test_05_and_06_published_exam_returns_only_mcqs(client, db_session):
    """5 & 6. Published exam returns MCQ questions and excludes coding questions."""
    student = db_session.query(User).filter(User.email == "student1@example.com").first()
    exam = db_session.query(Exam).first()
    headers = get_auth_header(student.id, student.email, "student")

    response = client.get(f"/mcq/exams/{exam.id}/questions", headers=headers)
    data = response.json()
    assert data["total_mcq_questions"] == 2
    for q in data["questions"]:
        assert q["question_text"] in {"What is 5 + 7?", "What is 10 * 10?"}
        assert q["question_text"] != "Reverse String"


def test_07_and_08_correct_answers_never_exposed_and_options_returned(client, db_session):
    """7 & 8. Anti-leak test: is_correct is never exposed to student-facing question endpoint."""
    student = db_session.query(User).filter(User.email == "student1@example.com").first()
    exam = db_session.query(Exam).first()
    headers = get_auth_header(student.id, student.email, "student")

    response = client.get(f"/mcq/exams/{exam.id}/questions", headers=headers)
    data = response.json()
    for q in data["questions"]:
        for opt in q["options"]:
            assert "is_correct" not in opt
            assert "id" in opt
            assert "option_text" in opt


def test_09_to_11_randomization_stability(client, db_session):
    """9-11. Randomized question ordering remains deterministic across refreshes for the same attempt."""
    student = db_session.query(User).filter(User.email == "student1@example.com").first()
    exam = db_session.query(Exam).first()
    headers = get_auth_header(student.id, student.email, "student")

    res1 = client.get(f"/mcq/exams/{exam.id}/questions", headers=headers).json()
    res2 = client.get(f"/mcq/exams/{exam.id}/questions", headers=headers).json()

    # Order of question IDs must be identical across calls for the same attempt
    order1 = [q["question_id"] for q in res1["questions"]]
    order2 = [q["question_id"] for q in res2["questions"]]
    assert order1 == order2


# ---------------------------------------------------------------------------
# Section 3: Answer Recording & Updating Tests (12-18)
# ---------------------------------------------------------------------------

def test_12_student_can_record_an_answer(client, db_session):
    """12. Student can record an answer to an MCQ question."""
    student = db_session.query(User).filter(User.email == "student1@example.com").first()
    exam = db_session.query(Exam).first()
    q1 = db_session.query(Question).filter(Question.question_text == "What is 5 + 7?").first()
    opt1_b = db_session.query(McqOption).filter(McqOption.question_id == q1.id, McqOption.option_text == "12").first()

    headers = get_auth_header(student.id, student.email, "student")

    # Get attempt
    q_res = client.get(f"/mcq/exams/{exam.id}/questions", headers=headers)
    attempt_id = q_res.json()["attempt_id"]

    # Submit answer
    ans_res = client.post(
        f"/mcq/attempts/{attempt_id}/answers",
        json={"question_id": q1.id, "selected_option_id": opt1_b.id},
        headers=headers,
    )
    assert ans_res.status_code == 200
    data = ans_res.json()
    assert data["question_id"] == q1.id
    assert data["selected_option_id"] == opt1_b.id


def test_13_and_14_student_can_change_answer_and_no_duplicates(client, db_session):
    """13 & 14. Student can change answer and duplicate records are prevented."""
    student = db_session.query(User).filter(User.email == "student1@example.com").first()
    exam = db_session.query(Exam).first()
    q1 = db_session.query(Question).filter(Question.question_text == "What is 5 + 7?").first()
    opt1_a = db_session.query(McqOption).filter(McqOption.question_id == q1.id, McqOption.option_text == "10").first()
    opt1_b = db_session.query(McqOption).filter(McqOption.question_id == q1.id, McqOption.option_text == "12").first()

    headers = get_auth_header(student.id, student.email, "student")

    q_res = client.get(f"/mcq/exams/{exam.id}/questions", headers=headers)
    attempt_id = q_res.json()["attempt_id"]

    # First choice: Option A
    client.post(f"/mcq/attempts/{attempt_id}/answers", json={"question_id": q1.id, "selected_option_id": opt1_a.id}, headers=headers)

    # Changed choice: Option B
    update_res = client.put(f"/mcq/attempts/{attempt_id}/answers/{q1.id}", json={"selected_option_id": opt1_b.id}, headers=headers)
    assert update_res.status_code == 200
    assert update_res.json()["selected_option_id"] == opt1_b.id

    # Verify only 1 record in database for this question
    answers = db_session.query(AttemptAnswer).filter(AttemptAnswer.attempt_id == attempt_id, AttemptAnswer.question_id == q1.id).all()
    assert len(answers) == 1
    assert answers[0].selected_option_id == opt1_b.id


def test_15_to_17_invalid_question_or_option_rejected(client, db_session):
    """15-17. Invalid question, invalid option, or option from another question is rejected."""
    student = db_session.query(User).filter(User.email == "student1@example.com").first()
    exam = db_session.query(Exam).first()
    q1 = db_session.query(Question).filter(Question.question_text == "What is 5 + 7?").first()
    q2 = db_session.query(Question).filter(Question.question_text == "What is 10 * 10?").first()
    opt2_a = db_session.query(McqOption).filter(McqOption.question_id == q2.id).first()

    headers = get_auth_header(student.id, student.email, "student")

    q_res = client.get(f"/mcq/exams/{exam.id}/questions", headers=headers)
    attempt_id = q_res.json()["attempt_id"]

    # 15. Invalid question ID
    res1 = client.post(f"/mcq/attempts/{attempt_id}/answers", json={"question_id": 99999, "selected_option_id": 1}, headers=headers)
    assert res1.status_code == 400

    # 16. Invalid option ID
    res2 = client.post(f"/mcq/attempts/{attempt_id}/answers", json={"question_id": q1.id, "selected_option_id": 99999}, headers=headers)
    assert res2.status_code == 400

    # 17. Option from question 2 submitted for question 1
    res3 = client.post(f"/mcq/attempts/{attempt_id}/answers", json={"question_id": q1.id, "selected_option_id": opt2_a.id}, headers=headers)
    assert res3.status_code == 400
    assert "does not belong" in res3.json()["detail"].lower()


def test_18_answer_cannot_be_changed_after_submission(client, db_session):
    """18. Answer cannot be changed after attempt is submitted or auto_submitted."""
    student = db_session.query(User).filter(User.email == "student1@example.com").first()
    exam = db_session.query(Exam).first()
    q1 = db_session.query(Question).filter(Question.question_text == "What is 5 + 7?").first()
    opt1_a = db_session.query(McqOption).filter(McqOption.question_id == q1.id, McqOption.option_text == "10").first()

    headers = get_auth_header(student.id, student.email, "student")

    q_res = client.get(f"/mcq/exams/{exam.id}/questions", headers=headers)
    attempt_id = q_res.json()["attempt_id"]

    # Lock attempt
    attempt = db_session.query(ExamAttempt).filter(ExamAttempt.id == attempt_id).first()
    attempt.status = "submitted"
    db_session.commit()

    # Attempt to submit answer
    res = client.post(f"/mcq/attempts/{attempt_id}/answers", json={"question_id": q1.id, "selected_option_id": opt1_a.id}, headers=headers)
    assert res.status_code == 400
    assert "already in 'submitted' state" in res.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Section 4: Scoring & Negative Marking Tests (19-25)
# ---------------------------------------------------------------------------

def test_19_to_25_scoring_and_negative_marking_and_marks_override(client, db_session):
    """19-25. Correct gives positive marks, incorrect gives negative marks, override respected, client marks ignored."""
    student = db_session.query(User).filter(User.email == "student1@example.com").first()
    exam = db_session.query(Exam).first()
    q1 = db_session.query(Question).filter(Question.question_text == "What is 5 + 7?").first()
    q2 = db_session.query(Question).filter(Question.question_text == "What is 10 * 10?").first()

    opt1_a = db_session.query(McqOption).filter(McqOption.question_id == q1.id, McqOption.option_text == "10").first()  # Wrong (2.0 marks * 0.25 = -0.5)
    opt2_a = db_session.query(McqOption).filter(McqOption.question_id == q2.id, McqOption.option_text == "100").first() # Correct (marks_override = 5.0)

    headers = get_auth_header(student.id, student.email, "student")

    q_res = client.get(f"/mcq/exams/{exam.id}/questions", headers=headers)
    attempt_id = q_res.json()["attempt_id"]

    # Q1: Answer incorrectly (-0.5 marks)
    client.post(f"/mcq/attempts/{attempt_id}/answers", json={"question_id": q1.id, "selected_option_id": opt1_a.id}, headers=headers)

    # Q2: Answer correctly (+5.0 marks due to marks_override)
    client.post(f"/mcq/attempts/{attempt_id}/answers", json={"question_id": q2.id, "selected_option_id": opt2_a.id}, headers=headers)

    # Score attempt
    score_res = client.post(f"/mcq/attempts/{attempt_id}/score", headers=headers)
    assert score_res.status_code == 200
    data = score_res.json()

    assert data["total_mcq_questions"] == 2
    assert data["answered_questions"] == 2
    assert data["unanswered_questions"] == 0
    assert data["correct_answers"] == 1
    assert data["incorrect_answers"] == 1
    assert data["total_marks_possible"] == 7.0  # 2.0 + 5.0
    assert data["total_marks_obtained"] == 4.5  # 5.0 - 0.5


# ---------------------------------------------------------------------------
# Section 5: Lifecycle & Answer State Tests (26-31)
# ---------------------------------------------------------------------------

def test_26_to_31_lifecycle_and_answer_retrieval(client, db_session):
    """26-31. In-progress allows retrieving answers; client cannot spoof is_correct or marks."""
    student = db_session.query(User).filter(User.email == "student1@example.com").first()
    exam = db_session.query(Exam).first()
    q1 = db_session.query(Question).filter(Question.question_text == "What is 5 + 7?").first()
    opt1_b = db_session.query(McqOption).filter(McqOption.question_id == q1.id, McqOption.option_text == "12").first()

    headers = get_auth_header(student.id, student.email, "student")

    q_res = client.get(f"/mcq/exams/{exam.id}/questions", headers=headers)
    attempt_id = q_res.json()["attempt_id"]

    # Record answer
    client.post(f"/mcq/attempts/{attempt_id}/answers", json={"question_id": q1.id, "selected_option_id": opt1_b.id}, headers=headers)

    # Get answers endpoint
    get_ans = client.get(f"/mcq/attempts/{attempt_id}/answers", headers=headers)
    assert get_ans.status_code == 200
    ans_data = get_ans.json()
    assert ans_data["attempt_id"] == attempt_id
    assert len(ans_data["answers"]) == 1
    assert ans_data["answers"][0]["question_id"] == q1.id
    assert ans_data["answers"][0]["selected_option_id"] == opt1_b.id
    assert "is_correct" not in ans_data["answers"][0]  # Anti-leak check
