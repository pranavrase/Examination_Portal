import pytest
from unittest.mock import patch
from sqlalchemy.exc import SQLAlchemyError
from app.models.user import User
from app.models.role import Role
from app.models.exam import Exam, ExamSettings, ExamAssignment
from app.core.security import hash_password, create_access_token
from app.services.role_service import seed_default_roles
from app.schemas.exam import ExamCreate, ExamSettingsCreate, ExamAssignmentCreate
from app.services import exam_service


@pytest.fixture(autouse=True)
def setup_test_users(db_session):
    """Seed default roles and create baseline users for exam tests."""
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

    # 3. Examiner 2 (Other Examiner)
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

    # 4. Student 1
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

    # 5. Student 2
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

    db_session.commit()


def get_auth_header(user_id: int, email: str, role: str) -> dict:
    token = create_access_token(user_id=user_id, email=email, role=role)
    return {"Authorization": f"Bearer {token}"}


def sample_exam_payload(title="Aptitude & Reasoning Assessment"):
    return {
        "title": title,
        "description": "Comprehensive evaluation of quantitative aptitude and logical reasoning.",
        "settings": {
            "duration_minutes": 60,
            "total_marks": 100.0,
            "passing_percentage": 40.0,
            "negative_marking_ratio": 0.25,
            "randomize_questions": True,
            "randomize_options": True,
        },
    }


# ---------------------------------------------------------------------------
# Test Cases
# ---------------------------------------------------------------------------

def test_01_examiner_can_create_exam(client, db_session):
    """1. Examiner can create an exam."""
    examiner = db_session.query(User).filter(User.email == "examiner1@example.com").first()
    headers = get_auth_header(examiner.id, examiner.email, "examiner")

    payload = sample_exam_payload("Examiner 1 Exam")
    response = client.post("/exams", json=payload, headers=headers)

    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Examiner 1 Exam"
    assert data["created_by"] == examiner.id
    assert data["status"] == "draft"
    assert data["settings"]["duration_minutes"] == 60
    assert data["settings"]["total_marks"] == 100.0
    assert data["settings"]["passing_percentage"] == 40.0
    assert data["settings"]["negative_marking_ratio"] == 0.25


def test_02_admin_can_create_exam(client, db_session):
    """2. Admin can create an exam."""
    admin = db_session.query(User).filter(User.email == "admin@example.com").first()
    headers = get_auth_header(admin.id, admin.email, "admin")

    payload = sample_exam_payload("Admin Created Exam")
    response = client.post("/exams", json=payload, headers=headers)

    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Admin Created Exam"
    assert data["created_by"] == admin.id
    assert data["status"] == "draft"


def test_03_unauthenticated_user_cannot_create_exam(client):
    """3. Unauthenticated user cannot create an exam."""
    payload = sample_exam_payload()
    response = client.post("/exams", json=payload)
    assert response.status_code == 401


def test_04_examiner_can_retrieve_own_exam(client, db_session):
    """4. Examiner can retrieve their own exam."""
    examiner = db_session.query(User).filter(User.email == "examiner1@example.com").first()
    headers = get_auth_header(examiner.id, examiner.email, "examiner")

    create_res = client.post("/exams", json=sample_exam_payload(), headers=headers)
    exam_id = create_res.json()["id"]

    response = client.get(f"/exams/{exam_id}", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == exam_id
    assert data["created_by"] == examiner.id
    assert data["settings"] is not None


def test_05_examiner_cannot_modify_another_examiners_exam(client, db_session):
    """5. Examiner cannot view or modify another examiner's exam."""
    examiner1 = db_session.query(User).filter(User.email == "examiner1@example.com").first()
    examiner2 = db_session.query(User).filter(User.email == "examiner2@example.com").first()

    headers1 = get_auth_header(examiner1.id, examiner1.email, "examiner")
    headers2 = get_auth_header(examiner2.id, examiner2.email, "examiner")

    # Examiner 1 creates exam
    create_res = client.post("/exams", json=sample_exam_payload("Exam 1"), headers=headers1)
    exam_id = create_res.json()["id"]

    # Examiner 2 tries to view Exam 1
    get_res = client.get(f"/exams/{exam_id}", headers=headers2)
    assert get_res.status_code == 403

    # Examiner 2 tries to update Exam 1
    update_res = client.put(f"/exams/{exam_id}", json={"title": "Hacked Title"}, headers=headers2)
    assert update_res.status_code == 403

    # Examiner 2 tries to delete Exam 1
    del_res = client.delete(f"/exams/{exam_id}", headers=headers2)
    assert del_res.status_code == 403


def test_06_admin_can_modify_any_exam(client, db_session):
    """6. Admin can modify any exam."""
    examiner = db_session.query(User).filter(User.email == "examiner1@example.com").first()
    admin = db_session.query(User).filter(User.email == "admin@example.com").first()

    headers_examiner = get_auth_header(examiner.id, examiner.email, "examiner")
    headers_admin = get_auth_header(admin.id, admin.email, "admin")

    # Examiner creates exam
    create_res = client.post("/exams", json=sample_exam_payload("Original Title"), headers=headers_examiner)
    exam_id = create_res.json()["id"]

    # Admin modifies exam
    update_res = client.put(
        f"/exams/{exam_id}",
        json={"title": "Admin Updated Title", "description": "Admin Updated Description"},
        headers=headers_admin,
    )
    assert update_res.status_code == 200
    data = update_res.json()
    assert data["title"] == "Admin Updated Title"
    assert data["description"] == "Admin Updated Description"


def test_07_exam_settings_validation_works(client, db_session):
    """7. Exam settings validation rejects negative marking ratio < 0 or negative marks."""
    examiner = db_session.query(User).filter(User.email == "examiner1@example.com").first()
    headers = get_auth_header(examiner.id, examiner.email, "examiner")

    payload = sample_exam_payload()
    payload["settings"]["negative_marking_ratio"] = -0.5
    response = client.post("/exams", json=payload, headers=headers)
    assert response.status_code == 422


def test_08_passing_percentage_cannot_exceed_100(client, db_session):
    """8. Passing percentage cannot exceed 100."""
    examiner = db_session.query(User).filter(User.email == "examiner1@example.com").first()
    headers = get_auth_header(examiner.id, examiner.email, "examiner")

    payload = sample_exam_payload()
    payload["settings"]["passing_percentage"] = 105.0
    response = client.post("/exams", json=payload, headers=headers)
    assert response.status_code == 422


def test_09_duration_cannot_be_zero_or_negative(client, db_session):
    """9. Duration cannot be zero or negative."""
    examiner = db_session.query(User).filter(User.email == "examiner1@example.com").first()
    headers = get_auth_header(examiner.id, examiner.email, "examiner")

    # Zero duration
    payload0 = sample_exam_payload()
    payload0["settings"]["duration_minutes"] = 0
    res0 = client.post("/exams", json=payload0, headers=headers)
    assert res0.status_code == 422

    # Negative duration
    payload_neg = sample_exam_payload()
    payload_neg["settings"]["duration_minutes"] = -15
    res_neg = client.post("/exams", json=payload_neg, headers=headers)
    assert res_neg.status_code == 422


def test_10_draft_exam_can_be_published(client, db_session):
    """10. Draft exam can be published."""
    examiner = db_session.query(User).filter(User.email == "examiner1@example.com").first()
    headers = get_auth_header(examiner.id, examiner.email, "examiner")

    create_res = client.post("/exams", json=sample_exam_payload(), headers=headers)
    exam_id = create_res.json()["id"]

    pub_res = client.post(f"/exams/{exam_id}/publish", headers=headers)
    assert pub_res.status_code == 200
    data = pub_res.json()
    assert data["status"] == "published"


def test_11_already_published_exam_cannot_be_published_again(client, db_session):
    """11. Already published exam cannot be published again."""
    examiner = db_session.query(User).filter(User.email == "examiner1@example.com").first()
    headers = get_auth_header(examiner.id, examiner.email, "examiner")

    create_res = client.post("/exams", json=sample_exam_payload(), headers=headers)
    exam_id = create_res.json()["id"]

    # First publish
    client.post(f"/exams/{exam_id}/publish", headers=headers)

    # Second publish attempt
    pub_res2 = client.post(f"/exams/{exam_id}/publish", headers=headers)
    assert pub_res2.status_code == 400
    assert "already published" in pub_res2.json()["detail"].lower()


def test_12_invalid_lifecycle_transitions_rejected(client, db_session):
    """12. Invalid lifecycle transitions (e.g. deleting published exam) are rejected."""
    examiner = db_session.query(User).filter(User.email == "examiner1@example.com").first()
    headers = get_auth_header(examiner.id, examiner.email, "examiner")

    create_res = client.post("/exams", json=sample_exam_payload(), headers=headers)
    exam_id = create_res.json()["id"]

    # Publish the exam
    client.post(f"/exams/{exam_id}/publish", headers=headers)

    # Attempt to delete published exam
    del_res = client.delete(f"/exams/{exam_id}", headers=headers)
    assert del_res.status_code == 400
    assert "cannot delete" in del_res.json()["detail"].lower()


def test_13_student_can_be_assigned_to_an_exam(client, db_session):
    """13. Student can be assigned to an exam."""
    examiner = db_session.query(User).filter(User.email == "examiner1@example.com").first()
    student = db_session.query(User).filter(User.email == "student1@example.com").first()
    headers = get_auth_header(examiner.id, examiner.email, "examiner")

    create_res = client.post("/exams", json=sample_exam_payload(), headers=headers)
    exam_id = create_res.json()["id"]

    assign_payload = {
        "student_ids": [student.id],
    }
    assign_res = client.post(f"/exams/{exam_id}/assign", json=assign_payload, headers=headers)
    assert assign_res.status_code == 201
    data = assign_res.json()
    assert data["assigned_count"] == 1
    assert data["assignments"][0]["student_id"] == student.id
    assert data["assignments"][0]["exam_id"] == exam_id


def test_14_duplicate_assignment_is_rejected(client, db_session):
    """14. Duplicate assignment of the same student is rejected with 409."""
    examiner = db_session.query(User).filter(User.email == "examiner1@example.com").first()
    student = db_session.query(User).filter(User.email == "student1@example.com").first()
    headers = get_auth_header(examiner.id, examiner.email, "examiner")

    create_res = client.post("/exams", json=sample_exam_payload(), headers=headers)
    exam_id = create_res.json()["id"]

    assign_payload = {"student_ids": [student.id]}
    # First assignment
    res1 = client.post(f"/exams/{exam_id}/assign", json=assign_payload, headers=headers)
    assert res1.status_code == 201

    # Second duplicate assignment
    res2 = client.post(f"/exams/{exam_id}/assign", json=assign_payload, headers=headers)
    assert res2.status_code == 409
    assert "already assigned" in res2.json()["detail"].lower()


def test_15_non_student_users_cannot_be_assigned(client, db_session):
    """15. Non-student users (e.g. examiner or admin) cannot be assigned to an exam."""
    examiner1 = db_session.query(User).filter(User.email == "examiner1@example.com").first()
    examiner2 = db_session.query(User).filter(User.email == "examiner2@example.com").first()
    headers = get_auth_header(examiner1.id, examiner1.email, "examiner")

    create_res = client.post("/exams", json=sample_exam_payload(), headers=headers)
    exam_id = create_res.json()["id"]

    assign_payload = {"student_ids": [examiner2.id]}
    response = client.post(f"/exams/{exam_id}/assign", json=assign_payload, headers=headers)
    assert response.status_code == 400
    assert "student" in response.json()["detail"].lower()


def test_16_examiner_cannot_assign_another_examiners_exam(client, db_session):
    """16. Examiner cannot assign students to another examiner's exam."""
    examiner1 = db_session.query(User).filter(User.email == "examiner1@example.com").first()
    examiner2 = db_session.query(User).filter(User.email == "examiner2@example.com").first()
    student = db_session.query(User).filter(User.email == "student1@example.com").first()

    headers1 = get_auth_header(examiner1.id, examiner1.email, "examiner")
    headers2 = get_auth_header(examiner2.id, examiner2.email, "examiner")

    create_res = client.post("/exams", json=sample_exam_payload(), headers=headers1)
    exam_id = create_res.json()["id"]

    assign_payload = {"student_ids": [student.id]}
    assign_res = client.post(f"/exams/{exam_id}/assign", json=assign_payload, headers=headers2)
    assert assign_res.status_code == 403


def test_17_admin_can_assign_any_exam(client, db_session):
    """17. Admin can assign students to any exam."""
    examiner = db_session.query(User).filter(User.email == "examiner1@example.com").first()
    admin = db_session.query(User).filter(User.email == "admin@example.com").first()
    student = db_session.query(User).filter(User.email == "student1@example.com").first()

    headers_examiner = get_auth_header(examiner.id, examiner.email, "examiner")
    headers_admin = get_auth_header(admin.id, admin.email, "admin")

    create_res = client.post("/exams", json=sample_exam_payload(), headers=headers_examiner)
    exam_id = create_res.json()["id"]

    assign_payload = {"student_ids": [student.id]}
    assign_res = client.post(f"/exams/{exam_id}/assign", json=assign_payload, headers=headers_admin)
    assert assign_res.status_code == 201
    assert assign_res.json()["assigned_count"] == 1


def test_18_non_authorized_users_receive_403(client, db_session):
    """18. Non-authorized users (e.g. students) receive 403 on exam management endpoints."""
    student = db_session.query(User).filter(User.email == "student1@example.com").first()
    headers = get_auth_header(student.id, student.email, "student")

    # Student cannot create exam
    res1 = client.post("/exams", json=sample_exam_payload(), headers=headers)
    assert res1.status_code == 403

    # Student cannot list exams on management route
    res2 = client.get("/exams", headers=headers)
    assert res2.status_code == 403


def test_19_missing_exam_returns_404(client, db_session):
    """19. Missing exam returns 404."""
    admin = db_session.query(User).filter(User.email == "admin@example.com").first()
    headers = get_auth_header(admin.id, admin.email, "admin")

    response = client.get("/exams/999999", headers=headers)
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_20_database_rollback_works_on_failure(client, db_session):
    """20. Database rollback ensures state consistency when an operation fails."""
    examiner = db_session.query(User).filter(User.email == "examiner1@example.com").first()

    exam_in = ExamCreate(
        title="Rollback Test Exam",
        description="Testing atomic transaction rollback",
        settings=ExamSettingsCreate(
            duration_minutes=45,
            total_marks=50.0,
            passing_percentage=50.0,
            negative_marking_ratio=0.0,
        ),
    )

    # Simulate database error on commit
    with patch.object(db_session, "commit", side_effect=SQLAlchemyError("Simulated DB connection error")):
        with pytest.raises(Exception) as exc_info:
            exam_service.create_exam(db=db_session, exam_in=exam_in, creator_id=examiner.id)
        assert "500" in str(exc_info.value) or "Simulated" in str(exc_info.value)

    # Verify no partial exam record was committed
    persisted = db_session.query(Exam).filter(Exam.title == "Rollback Test Exam").first()
    assert persisted is None


def test_21_list_exams_filtering_and_pagination(client, db_session):
    """21. List exams respects ownership, search, and pagination."""
    examiner1 = db_session.query(User).filter(User.email == "examiner1@example.com").first()
    examiner2 = db_session.query(User).filter(User.email == "examiner2@example.com").first()
    admin = db_session.query(User).filter(User.email == "admin@example.com").first()

    headers1 = get_auth_header(examiner1.id, examiner1.email, "examiner")
    headers2 = get_auth_header(examiner2.id, examiner2.email, "examiner")
    headers_admin = get_auth_header(admin.id, admin.email, "admin")

    # Examiner 1 creates 2 exams
    client.post("/exams", json=sample_exam_payload("Math 101"), headers=headers1)
    client.post("/exams", json=sample_exam_payload("Physics 101"), headers=headers1)

    # Examiner 2 creates 1 exam
    client.post("/exams", json=sample_exam_payload("Chemistry 101"), headers=headers2)

    # Examiner 1 lists exams (should only see 2)
    list1 = client.get("/exams", headers=headers1).json()
    assert list1["total"] == 2
    titles1 = [e["title"] for e in list1["items"]]
    assert "Chemistry 101" not in titles1

    # Admin lists exams (should see all 3)
    list_admin = client.get("/exams", headers=headers_admin).json()
    assert list_admin["total"] >= 3

    # Search filter
    search_res = client.get("/exams?search=Math", headers=headers1).json()
    assert search_res["total"] == 1
    assert search_res["items"][0]["title"] == "Math 101"


def test_22_update_settings_and_unassign_student(client, db_session):
    """22. Update settings and unassign student functionality."""
    examiner = db_session.query(User).filter(User.email == "examiner1@example.com").first()
    student = db_session.query(User).filter(User.email == "student1@example.com").first()
    headers = get_auth_header(examiner.id, examiner.email, "examiner")

    create_res = client.post("/exams", json=sample_exam_payload(), headers=headers)
    exam_id = create_res.json()["id"]

    # Update settings
    settings_res = client.put(
        f"/exams/{exam_id}/settings",
        json={"duration_minutes": 90, "total_marks": 150.0},
        headers=headers,
    )
    assert settings_res.status_code == 200
    assert settings_res.json()["duration_minutes"] == 90
    assert settings_res.json()["total_marks"] == 150.0

    # Assign student
    client.post(f"/exams/{exam_id}/assign", json={"student_id": student.id}, headers=headers)

    # List assignments
    assignments_res = client.get(f"/exams/{exam_id}/assignments", headers=headers)
    assert assignments_res.status_code == 200
    assert assignments_res.json()["total"] == 1

    # Unassign student
    unassign_res = client.delete(f"/exams/{exam_id}/assignments/{student.id}", headers=headers)
    assert unassign_res.status_code == 200

    # Verify unassigned
    assignments_after = client.get(f"/exams/{exam_id}/assignments", headers=headers)
    assert assignments_after.json()["total"] == 0
