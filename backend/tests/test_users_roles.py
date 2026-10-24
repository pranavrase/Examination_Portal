import pytest
from app.models.user import User
from app.models.role import Role
from app.core.security import hash_password, create_access_token
from app.services.role_service import seed_default_roles


@pytest.fixture(autouse=True)
def setup_roles_and_users(db_session):
    """Seed default roles and create baseline users for testing."""
    seed_default_roles(db_session)

    # 1. Admin user
    admin = User(
        email="admin@example.com",
        full_name="System Administrator",
        password_hash=hash_password("AdminPassword123"),
        role="admin",
        is_active=True
    )
    admin_role = db_session.query(Role).filter(Role.name == "admin").first()
    if admin_role:
        admin.roles.append(admin_role)
    db_session.add(admin)

    # 2. Student user
    student = User(
        email="student@example.com",
        full_name="Normal Student",
        password_hash=hash_password("StudentPassword123"),
        role="student",
        is_active=True
    )
    student_role = db_session.query(Role).filter(Role.name == "student").first()
    if student_role:
        student.roles.append(student_role)
    db_session.add(student)

    # 3. Examiner user
    examiner = User(
        email="examiner@example.com",
        full_name="Exam Examiner",
        password_hash=hash_password("ExaminerPassword123"),
        role="examiner",
        is_active=True
    )
    examiner_role = db_session.query(Role).filter(Role.name == "examiner").first()
    if examiner_role:
        examiner.roles.append(examiner_role)
    db_session.add(examiner)

    db_session.commit()


def get_auth_header(user_id: int, email: str, role: str) -> dict:
    token = create_access_token(user_id=user_id, email=email, role=role)
    return {"Authorization": f"Bearer {token}"}


def test_01_admin_can_list_users(client, db_session):
    """1. Admin can list users."""
    admin = db_session.query(User).filter(User.email == "admin@example.com").first()
    headers = get_auth_header(admin.id, admin.email, "admin")

    response = client.get("/users", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert data["total"] >= 3
    assert data["page"] == 1


def test_02_student_cannot_list_users(client, db_session):
    """2. Student cannot list users."""
    student = db_session.query(User).filter(User.email == "student@example.com").first()
    headers = get_auth_header(student.id, student.email, "student")

    response = client.get("/users", headers=headers)
    assert response.status_code == 403
    assert "restricted" in response.json()["detail"].lower()


def test_03_examiner_cannot_list_users(client, db_session):
    """3. Examiner cannot list users."""
    examiner = db_session.query(User).filter(User.email == "examiner@example.com").first()
    headers = get_auth_header(examiner.id, examiner.email, "examiner")

    response = client.get("/users", headers=headers)
    assert response.status_code == 403


def test_04_admin_can_retrieve_a_user(client, db_session):
    """4. Admin can retrieve a user."""
    admin = db_session.query(User).filter(User.email == "admin@example.com").first()
    student = db_session.query(User).filter(User.email == "student@example.com").first()
    headers = get_auth_header(admin.id, admin.email, "admin")

    response = client.get(f"/users/{student.id}", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == student.id
    assert data["email"] == "student@example.com"
    assert "password_hash" not in data


def test_05_admin_can_assign_a_role(client, db_session):
    """5. Admin can assign a role."""
    admin = db_session.query(User).filter(User.email == "admin@example.com").first()
    student = db_session.query(User).filter(User.email == "student@example.com").first()
    headers = get_auth_header(admin.id, admin.email, "admin")

    response = client.put(f"/users/{student.id}/role", json={"role": "examiner"}, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["role"] == "examiner"


def test_06_duplicate_role_assignment_rejected(client, db_session):
    """6. Duplicate role assignment is rejected safely."""
    admin = db_session.query(User).filter(User.email == "admin@example.com").first()
    student = db_session.query(User).filter(User.email == "student@example.com").first()
    headers = get_auth_header(admin.id, admin.email, "admin")

    # Assign role once
    client.post(f"/users/{student.id}/roles", json={"role_name": "examiner"}, headers=headers)

    # Attempt to assign the same role again
    response = client.post(f"/users/{student.id}/roles", json={"role_name": "examiner"}, headers=headers)
    assert response.status_code == 400
    assert "already has role" in response.json()["detail"].lower()


def test_07_admin_can_deactivate_a_user(client, db_session):
    """7. Admin can deactivate a user."""
    admin = db_session.query(User).filter(User.email == "admin@example.com").first()
    student = db_session.query(User).filter(User.email == "student@example.com").first()
    headers = get_auth_header(admin.id, admin.email, "admin")

    response = client.delete(f"/users/{student.id}", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["is_active"] is False


def test_08_deactivated_user_cannot_authenticate(client, db_session):
    """8. Deactivated user cannot authenticate."""
    admin = db_session.query(User).filter(User.email == "admin@example.com").first()
    student = db_session.query(User).filter(User.email == "student@example.com").first()
    headers = get_auth_header(admin.id, admin.email, "admin")

    # Deactivate student
    client.delete(f"/users/{student.id}", headers=headers)

    # Attempt login as student
    login_res = client.post("/auth/login", json={"email": "student@example.com", "password": "StudentPassword123"})
    assert login_res.status_code == 403
    assert "inactive" in login_res.json()["detail"].lower()


def test_09_invalid_user_id_returns_404(client, db_session):
    """9. Invalid user ID returns 404."""
    admin = db_session.query(User).filter(User.email == "admin@example.com").first()
    headers = get_auth_header(admin.id, admin.email, "admin")

    response = client.get("/users/999999", headers=headers)
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_10_invalid_role_id_returns_404(client, db_session):
    """10. Invalid role ID returns 404."""
    admin = db_session.query(User).filter(User.email == "admin@example.com").first()
    headers = get_auth_header(admin.id, admin.email, "admin")

    response = client.delete("/roles/999999", headers=headers)
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_11_unauthorized_requests_return_401(client):
    """11. Unauthorized requests return 401."""
    response = client.get("/users")
    assert response.status_code == 401


def test_12_authenticated_non_admin_returns_403(client, db_session):
    """12. Authenticated non-admin requests return 403."""
    student = db_session.query(User).filter(User.email == "student@example.com").first()
    headers = get_auth_header(student.id, student.email, "student")

    # Try modifying user role
    response = client.put(f"/users/{student.id}/role", json={"role": "admin"}, headers=headers)
    assert response.status_code == 403

    # Try listing roles
    roles_res = client.get("/roles", headers=headers)
    assert roles_res.status_code == 403
