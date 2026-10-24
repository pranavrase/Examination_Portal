import io
import pytest
from unittest.mock import patch
from sqlalchemy.exc import SQLAlchemyError

from app.models.user import User
from app.models.role import Role
from app.models.question import QuestionCategory, Question, CodingTestCase
from app.core.security import hash_password, create_access_token
from app.services.role_service import seed_default_roles
from app.schemas.question import (
    MCQQuestionCreate,
    MCQOptionCreate,
    CodingQuestionFullCreate,
    CodingTestCaseCreate,
    QuestionCategoryCreate,
)
from app.services import question_service


@pytest.fixture(autouse=True)
def setup_question_bank_fixtures(db_session):
    """Seed default roles, users, and baseline question categories."""
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

    # 2. Examiner 1 (Owner)
    examiner1 = User(
        email="examiner1@example.com",
        full_name="Examiner One",
        password_hash=hash_password("ExaminerPass123"),
        role="examiner",
        is_active=True,
    )
    examiner_role = db_session.query(Role).filter(Role.name == "examiner").first()
    if examiner_role:
        examiner1.roles.append(examiner_role)
    db_session.add(examiner1)

    # 3. Examiner 2
    examiner2 = User(
        email="examiner2@example.com",
        full_name="Examiner Two",
        password_hash=hash_password("ExaminerPass123"),
        role="examiner",
        is_active=True,
    )
    if examiner_role:
        examiner2.roles.append(examiner_role)
    db_session.add(examiner2)

    # 4. Student
    student = User(
        email="student@example.com",
        full_name="Student User",
        password_hash=hash_password("StudentPass123"),
        role="student",
        is_active=True,
    )
    student_role = db_session.query(Role).filter(Role.name == "student").first()
    if student_role:
        student.roles.append(student_role)
    db_session.add(student)

    # Seed Baseline Categories
    cat_apt = QuestionCategory(name="aptitude", topic="Time & Work", difficulty="medium")
    cat_reas = QuestionCategory(name="reasoning", topic="Syzygy & Series", difficulty="easy")
    cat_code = QuestionCategory(name="coding", topic="Dynamic Programming", difficulty="hard")
    db_session.add_all([cat_apt, cat_reas, cat_code])

    db_session.commit()


def get_auth_header(user_id: int, email: str, role: str) -> dict:
    token = create_access_token(user_id=user_id, email=email, role=role)
    return {"Authorization": f"Bearer {token}"}


def sample_mcq_payload(category_id: int, title: str = "Sample MCQ Question"):
    return {
        "category_id": category_id,
        "question_type": "mcq",
        "question_text": title,
        "marks": 2.0,
        "options": [
            {"option_text": "Option A (Wrong)", "is_correct": False},
            {"option_text": "Option B (Right)", "is_correct": True},
            {"option_text": "Option C (Wrong)", "is_correct": False},
            {"option_text": "Option D (Wrong)", "is_correct": False},
        ],
    }


def sample_coding_payload(category_id: int, title: str = "Two Sum Problem"):
    return {
        "category_id": category_id,
        "question_type": "coding",
        "question_text": title,
        "marks": 10.0,
        "problem_statement": "Given an array of integers, return indices of the two numbers such that they add up to target.",
        "constraints": "2 <= nums.length <= 10^4",
        "allowed_languages": ["python", "java", "cpp", "c"],
        "time_limit_ms": 2000,
        "memory_limit_kb": 256000,
        "test_cases": [
            {"input": "[2,7,11,15]\n9", "expected_output": "[0,1]", "is_sample": True, "is_hidden": False},
            {"input": "[3,2,4]\n6", "expected_output": "[1,2]", "is_sample": False, "is_hidden": True},
        ],
    }


# ---------------------------------------------------------------------------
# Section 1: MCQ Tests (1-8)
# ---------------------------------------------------------------------------

def test_01_examiner_can_create_mcq(client, db_session):
    """1. Examiner can create MCQ."""
    examiner = db_session.query(User).filter(User.email == "examiner1@example.com").first()
    category = db_session.query(QuestionCategory).filter(QuestionCategory.name == "aptitude").first()
    headers = get_auth_header(examiner.id, examiner.email, "examiner")

    payload = sample_mcq_payload(category.id, "Find LCM of 12 and 18")
    response = client.post("/questions", json=payload, headers=headers)

    assert response.status_code == 201
    data = response.json()
    assert data["question_type"] == "mcq"
    assert data["question_text"] == "Find LCM of 12 and 18"
    assert data["created_by"] == examiner.id
    assert len(data["mcq_options"]) == 4


def test_02_admin_can_create_mcq(client, db_session):
    """2. Admin can create MCQ."""
    admin = db_session.query(User).filter(User.email == "admin@example.com").first()
    category = db_session.query(QuestionCategory).filter(QuestionCategory.name == "reasoning").first()
    headers = get_auth_header(admin.id, admin.email, "admin")

    payload = sample_mcq_payload(category.id, "Admin Reasoning MCQ")
    response = client.post("/questions", json=payload, headers=headers)

    assert response.status_code == 201
    assert response.json()["created_by"] == admin.id


def test_03_unauthenticated_user_cannot_create_mcq(client, db_session):
    """3. Unauthenticated user cannot create MCQ."""
    category = db_session.query(QuestionCategory).first()
    payload = sample_mcq_payload(category.id)
    response = client.post("/questions", json=payload)
    assert response.status_code == 401


def test_04_mcq_requires_at_least_two_options(client, db_session):
    """4. MCQ requires at least two options."""
    examiner = db_session.query(User).filter(User.email == "examiner1@example.com").first()
    category = db_session.query(QuestionCategory).first()
    headers = get_auth_header(examiner.id, examiner.email, "examiner")

    payload = sample_mcq_payload(category.id)
    payload["options"] = [{"option_text": "Single Option", "is_correct": True}]

    response = client.post("/questions", json=payload, headers=headers)
    assert response.status_code == 422


def test_05_mcq_requires_a_correct_option(client, db_session):
    """5. MCQ requires at least one correct option."""
    examiner = db_session.query(User).filter(User.email == "examiner1@example.com").first()
    category = db_session.query(QuestionCategory).first()
    headers = get_auth_header(examiner.id, examiner.email, "examiner")

    payload = sample_mcq_payload(category.id)
    for opt in payload["options"]:
        opt["is_correct"] = False

    response = client.post("/questions", json=payload, headers=headers)
    assert response.status_code == 422


def test_06_empty_option_text_is_rejected(client, db_session):
    """6. Empty option text is rejected."""
    examiner = db_session.query(User).filter(User.email == "examiner1@example.com").first()
    category = db_session.query(QuestionCategory).first()
    headers = get_auth_header(examiner.id, examiner.email, "examiner")

    payload = sample_mcq_payload(category.id)
    payload["options"][0]["option_text"] = "   "

    response = client.post("/questions", json=payload, headers=headers)
    assert response.status_code == 422


def test_07_invalid_category_is_rejected(client, db_session):
    """7. Invalid category is rejected with 404."""
    examiner = db_session.query(User).filter(User.email == "examiner1@example.com").first()
    headers = get_auth_header(examiner.id, examiner.email, "examiner")

    payload = sample_mcq_payload(category_id=99999)
    response = client.post("/questions", json=payload, headers=headers)
    assert response.status_code == 404


def test_08_invalid_marks_are_rejected(client, db_session):
    """8. Invalid marks (<= 0) are rejected."""
    examiner = db_session.query(User).filter(User.email == "examiner1@example.com").first()
    category = db_session.query(QuestionCategory).first()
    headers = get_auth_header(examiner.id, examiner.email, "examiner")

    # Zero marks
    payload0 = sample_mcq_payload(category.id)
    payload0["marks"] = 0
    res0 = client.post("/questions", json=payload0, headers=headers)
    assert res0.status_code == 422

    # Negative marks
    payload_neg = sample_mcq_payload(category.id)
    payload_neg["marks"] = -5.0
    res_neg = client.post("/questions", json=payload_neg, headers=headers)
    assert res_neg.status_code == 422


# ---------------------------------------------------------------------------
# Section 2: Coding Question Tests (9-13)
# ---------------------------------------------------------------------------

def test_09_examiner_can_create_coding_question(client, db_session):
    """9. Examiner can create coding question with test cases."""
    examiner = db_session.query(User).filter(User.email == "examiner1@example.com").first()
    category = db_session.query(QuestionCategory).filter(QuestionCategory.name == "coding").first()
    headers = get_auth_header(examiner.id, examiner.email, "examiner")

    payload = sample_coding_payload(category.id, "Reverse Linked List")
    response = client.post("/questions", json=payload, headers=headers)

    assert response.status_code == 201
    data = response.json()
    assert data["question_type"] == "coding"
    assert data["coding_details"]["problem_statement"] == payload["problem_statement"]
    assert data["coding_details"]["time_limit_ms"] == 2000
    assert len(data["coding_details"]["test_cases"]) == 2


def test_10_coding_question_requires_problem_statement(client, db_session):
    """10. Coding question requires non-empty problem statement."""
    examiner = db_session.query(User).filter(User.email == "examiner1@example.com").first()
    category = db_session.query(QuestionCategory).first()
    headers = get_auth_header(examiner.id, examiner.email, "examiner")

    payload = sample_coding_payload(category.id)
    payload["problem_statement"] = "   "

    response = client.post("/questions", json=payload, headers=headers)
    assert response.status_code == 422


def test_11_invalid_execution_limits_rejected(client, db_session):
    """11. Invalid execution limits (<= 0) are rejected."""
    examiner = db_session.query(User).filter(User.email == "examiner1@example.com").first()
    category = db_session.query(QuestionCategory).first()
    headers = get_auth_header(examiner.id, examiner.email, "examiner")

    payload = sample_coding_payload(category.id)
    payload["time_limit_ms"] = -500

    response = client.post("/questions", json=payload, headers=headers)
    assert response.status_code == 422


def test_12_unsupported_language_is_rejected(client, db_session):
    """12. Unsupported programming language is rejected."""
    examiner = db_session.query(User).filter(User.email == "examiner1@example.com").first()
    category = db_session.query(QuestionCategory).first()
    headers = get_auth_header(examiner.id, examiner.email, "examiner")

    payload = sample_coding_payload(category.id)
    payload["allowed_languages"] = ["brainfuck_lang"]

    response = client.post("/questions", json=payload, headers=headers)
    assert response.status_code == 422


def test_13_coding_question_cannot_receive_mcq_options(client, db_session):
    """13. Coding question cannot contain MCQ options."""
    examiner = db_session.query(User).filter(User.email == "examiner1@example.com").first()
    category = db_session.query(QuestionCategory).first()
    headers = get_auth_header(examiner.id, examiner.email, "examiner")

    payload = sample_coding_payload(category.id)
    payload["options"] = [{"option_text": "Invalid", "is_correct": True}]

    response = client.post("/questions", json=payload, headers=headers)
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Section 3: Coding Test Cases Tests (14-17)
# ---------------------------------------------------------------------------

def test_14_examiner_can_add_coding_test_cases(client, db_session):
    """14. Examiner can add coding test cases to existing coding question."""
    examiner = db_session.query(User).filter(User.email == "examiner1@example.com").first()
    category = db_session.query(QuestionCategory).first()
    headers = get_auth_header(examiner.id, examiner.email, "examiner")

    create_res = client.post("/questions", json=sample_coding_payload(category.id), headers=headers)
    question_id = create_res.json()["id"]

    test_cases_payload = [
        {"input": "[1,2,3]\n5", "expected_output": "[1,2]", "is_sample": True, "is_hidden": False},
        {"input": "[0,4,3,0]\n0", "expected_output": "[0,3]", "is_sample": False, "is_hidden": True},
    ]

    response = client.post(f"/questions/coding/{question_id}/test-cases", json=test_cases_payload, headers=headers)
    assert response.status_code == 201
    assert len(response.json()) == 2


def test_15_invalid_coding_question_id_returns_404(client, db_session):
    """15. Invalid coding question ID returns 404 when adding test cases."""
    examiner = db_session.query(User).filter(User.email == "examiner1@example.com").first()
    headers = get_auth_header(examiner.id, examiner.email, "examiner")

    test_cases_payload = [{"input": "test", "expected_output": "out", "is_sample": True, "is_hidden": False}]
    response = client.post("/questions/coding/99999/test-cases", json=test_cases_payload, headers=headers)
    assert response.status_code == 404


def test_16_sample_hidden_validation_works(client, db_session):
    """16. Test case cannot be both sample and hidden at the same time."""
    examiner = db_session.query(User).filter(User.email == "examiner1@example.com").first()
    category = db_session.query(QuestionCategory).first()
    headers = get_auth_header(examiner.id, examiner.email, "examiner")

    create_res = client.post("/questions", json=sample_coding_payload(category.id), headers=headers)
    question_id = create_res.json()["id"]

    invalid_tc = [{"input": "test", "expected_output": "out", "is_sample": True, "is_hidden": True}]
    response = client.post(f"/questions/coding/{question_id}/test-cases", json=invalid_tc, headers=headers)
    assert response.status_code == 422


def test_17_hidden_test_cases_handled_correctly(client, db_session):
    """17. Test cases are properly tagged as sample vs hidden."""
    examiner = db_session.query(User).filter(User.email == "examiner1@example.com").first()
    category = db_session.query(QuestionCategory).first()
    headers = get_auth_header(examiner.id, examiner.email, "examiner")

    create_res = client.post("/questions", json=sample_coding_payload(category.id), headers=headers)
    q_data = create_res.json()
    tcs = q_data["coding_details"]["test_cases"]

    sample_cases = [tc for tc in tcs if tc["is_sample"]]
    hidden_cases = [tc for tc in tcs if tc["is_hidden"]]
    assert len(sample_cases) == 1
    assert len(hidden_cases) == 1


# ---------------------------------------------------------------------------
# Section 4: CRUD & Ownership Tests (18-23)
# ---------------------------------------------------------------------------

def test_18_examiner_can_update_own_question(client, db_session):
    """18. Examiner can update their own question."""
    examiner = db_session.query(User).filter(User.email == "examiner1@example.com").first()
    category = db_session.query(QuestionCategory).first()
    headers = get_auth_header(examiner.id, examiner.email, "examiner")

    create_res = client.post("/questions", json=sample_mcq_payload(category.id, "Old Question"), headers=headers)
    question_id = create_res.json()["id"]

    update_res = client.put(f"/questions/{question_id}", json={"question_text": "Updated Question Text", "marks": 5.0}, headers=headers)
    assert update_res.status_code == 200
    assert update_res.json()["question_text"] == "Updated Question Text"
    assert update_res.json()["marks"] == 5.0


def test_19_examiner_cannot_update_another_examiners_question(client, db_session):
    """19. Examiner cannot update another examiner's question (403)."""
    examiner1 = db_session.query(User).filter(User.email == "examiner1@example.com").first()
    examiner2 = db_session.query(User).filter(User.email == "examiner2@example.com").first()
    category = db_session.query(QuestionCategory).first()

    headers1 = get_auth_header(examiner1.id, examiner1.email, "examiner")
    headers2 = get_auth_header(examiner2.id, examiner2.email, "examiner")

    create_res = client.post("/questions", json=sample_mcq_payload(category.id), headers=headers1)
    question_id = create_res.json()["id"]

    update_res = client.put(f"/questions/{question_id}", json={"question_text": "Hacked Text"}, headers=headers2)
    assert update_res.status_code == 403

    del_res = client.delete(f"/questions/{question_id}", headers=headers2)
    assert del_res.status_code == 403


def test_20_admin_can_update_any_question(client, db_session):
    """20. Admin can update any question."""
    examiner = db_session.query(User).filter(User.email == "examiner1@example.com").first()
    admin = db_session.query(User).filter(User.email == "admin@example.com").first()
    category = db_session.query(QuestionCategory).first()

    headers_examiner = get_auth_header(examiner.id, examiner.email, "examiner")
    headers_admin = get_auth_header(admin.id, admin.email, "admin")

    create_res = client.post("/questions", json=sample_mcq_payload(category.id), headers=headers_examiner)
    question_id = create_res.json()["id"]

    update_res = client.put(f"/questions/{question_id}", json={"question_text": "Admin Updated"}, headers=headers_admin)
    assert update_res.status_code == 200
    assert update_res.json()["question_text"] == "Admin Updated"


def test_21_examiner_can_delete_own_question(client, db_session):
    """21. Examiner can delete their own question."""
    examiner = db_session.query(User).filter(User.email == "examiner1@example.com").first()
    category = db_session.query(QuestionCategory).first()
    headers = get_auth_header(examiner.id, examiner.email, "examiner")

    create_res = client.post("/questions", json=sample_mcq_payload(category.id), headers=headers)
    question_id = create_res.json()["id"]

    del_res = client.delete(f"/questions/{question_id}", headers=headers)
    assert del_res.status_code == 200

    get_res = client.get(f"/questions/{question_id}", headers=headers)
    assert get_res.status_code == 404


def test_22_admin_can_delete_any_question(client, db_session):
    """22. Admin can delete any question."""
    examiner = db_session.query(User).filter(User.email == "examiner1@example.com").first()
    admin = db_session.query(User).filter(User.email == "admin@example.com").first()
    category = db_session.query(QuestionCategory).first()

    headers_examiner = get_auth_header(examiner.id, examiner.email, "examiner")
    headers_admin = get_auth_header(admin.id, admin.email, "admin")

    create_res = client.post("/questions", json=sample_mcq_payload(category.id), headers=headers_examiner)
    question_id = create_res.json()["id"]

    del_res = client.delete(f"/questions/{question_id}", headers=headers_admin)
    assert del_res.status_code == 200


def test_23_missing_question_returns_404(client, db_session):
    """23. Missing question returns 404."""
    admin = db_session.query(User).filter(User.email == "admin@example.com").first()
    headers = get_auth_header(admin.id, admin.email, "admin")

    response = client.get("/questions/999999", headers=headers)
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Section 5: Filtering & Pagination Tests (24-28)
# ---------------------------------------------------------------------------

def test_24_to_28_question_filtering_and_pagination(client, db_session):
    """24-28. Filter by category, topic, difficulty, question type, and pagination."""
    examiner = db_session.query(User).filter(User.email == "examiner1@example.com").first()
    cat_apt = db_session.query(QuestionCategory).filter(QuestionCategory.name == "aptitude").first()
    cat_code = db_session.query(QuestionCategory).filter(QuestionCategory.name == "coding").first()
    headers = get_auth_header(examiner.id, examiner.email, "examiner")

    # Create 3 questions
    client.post("/questions", json=sample_mcq_payload(cat_apt.id, "Aptitude Q1"), headers=headers)
    client.post("/questions", json=sample_mcq_payload(cat_apt.id, "Aptitude Q2"), headers=headers)
    client.post("/questions", json=sample_coding_payload(cat_code.id, "Coding Q1"), headers=headers)

    # 24. Filter by category
    res_cat = client.get("/questions?category=aptitude", headers=headers).json()
    assert res_cat["total"] == 2

    # 25. Filter by topic
    res_topic = client.get("/questions?topic=Dynamic%20Programming", headers=headers).json()
    assert res_topic["total"] == 1
    assert res_topic["items"][0]["question_text"] == "Coding Q1"

    # 26. Filter by difficulty
    res_diff = client.get("/questions?difficulty=hard", headers=headers).json()
    assert res_diff["total"] == 1

    # 27. Filter by question type
    res_mcq = client.get("/questions?question_type=mcq", headers=headers).json()
    assert res_mcq["total"] == 2
    res_coding = client.get("/questions?question_type=coding", headers=headers).json()
    assert res_coding["total"] == 1

    # 28. Pagination
    res_page = client.get("/questions?page=1&page_size=2", headers=headers).json()
    assert len(res_page["items"]) == 2
    assert res_page["total"] == 3


# ---------------------------------------------------------------------------
# Section 6: Bulk Import Tests (29-33)
# ---------------------------------------------------------------------------

def test_29_valid_csv_imports_successfully(client, db_session):
    """29. Valid CSV imports successfully."""
    examiner = db_session.query(User).filter(User.email == "examiner1@example.com").first()
    headers = get_auth_header(examiner.id, examiner.email, "examiner")

    csv_content = """question_type,category,topic,difficulty,question_text,marks,option_a,option_b,option_c,option_d,correct_option
mcq,aptitude,Percentages,medium,What is 20% of 150?,2,20,30,40,50,b
mcq,reasoning,Blood Relations,easy,A is father of B. Who is B?,1,Son,Daughter,Child,Uncle,c
"""
    files = {"file": ("questions.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    response = client.post("/questions/bulk-import", files=files, headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["successful_imports"] == 2
    assert data["failed_imports"] == 0


def test_30_invalid_file_type_rejected(client, db_session):
    """30. Invalid file type (e.g. .pdf) is rejected."""
    examiner = db_session.query(User).filter(User.email == "examiner1@example.com").first()
    headers = get_auth_header(examiner.id, examiner.email, "examiner")

    files = {"file": ("document.pdf", io.BytesIO(b"fake pdf"), "application/pdf")}
    response = client.post("/questions/bulk-import", files=files, headers=headers)
    assert response.status_code == 400
    assert "csv" in response.json()["detail"].lower()


def test_31_invalid_rows_return_meaningful_errors(client, db_session):
    """31. Invalid rows return meaningful row-level error reports."""
    examiner = db_session.query(User).filter(User.email == "examiner1@example.com").first()
    headers = get_auth_header(examiner.id, examiner.email, "examiner")

    csv_content = """question_type,category,topic,difficulty,question_text,marks,option_a,option_b,option_c,option_d,correct_option
mcq,aptitude,Profit,medium,,2,10,20,30,40,a
mcq,aptitude,Profit,medium,Valid Question,invalid_marks,10,20,30,40,a
mcq,aptitude,Profit,medium,Valid Question 2,2,10,20,30,40,z
"""
    files = {"file": ("questions.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    response = client.post("/questions/bulk-import", files=files, headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["failed_imports"] == 3
    assert len(data["errors"]) == 3
    assert data["errors"][0]["row_index"] == 2


def test_32_import_does_not_silently_create_malformed_questions(client, db_session):
    """32. Bulk import correctly processes mixed valid and invalid rows without corruption."""
    examiner = db_session.query(User).filter(User.email == "examiner1@example.com").first()
    headers = get_auth_header(examiner.id, examiner.email, "examiner")

    csv_content = """question_type,category,topic,difficulty,question_text,marks,option_a,option_b,option_c,option_d,correct_option
mcq,aptitude,Time,medium,Valid Question in mixed batch,2,10,20,30,40,a
invalid_type,aptitude,Time,medium,Bad Type,2,10,20,30,40,a
"""
    files = {"file": ("questions.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    response = client.post("/questions/bulk-import", files=files, headers=headers)

    data = response.json()
    assert data["successful_imports"] == 1
    assert data["failed_imports"] == 1


def test_33_transaction_rollback_on_db_failure(client, db_session):
    """33. Transaction rollback ensures database consistency on creation error."""
    examiner = db_session.query(User).filter(User.email == "examiner1@example.com").first()
    category = db_session.query(QuestionCategory).first()

    mcq_in = MCQQuestionCreate(
        category_id=category.id,
        question_type="mcq",
        question_text="Rollback Test MCQ",
        marks=2.0,
        options=[
            MCQOptionCreate(option_text="A", is_correct=True),
            MCQOptionCreate(option_text="B", is_correct=False),
        ],
    )

    with patch.object(db_session, "commit", side_effect=SQLAlchemyError("Simulated DB error")):
        with pytest.raises(Exception):
            question_service.create_mcq_question(db=db_session, mcq_in=mcq_in, creator_id=examiner.id)

    persisted = db_session.query(Question).filter(Question.question_text == "Rollback Test MCQ").first()
    assert persisted is None
