from datetime import timedelta
import pytest
from app.core.security import create_access_token
from app.models.user import User
from app.core.security import hash_password


def test_01_successful_registration(client):
    """1. Successful registration"""
    payload = {
        "email": "student1@example.com",
        "password": "SecurePassword123",
        "full_name": "John Student",
        "role": "student"
    }
    response = client.post("/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "student1@example.com"
    assert data["full_name"] == "John Student"
    assert data["role"] == "student"
    assert data["is_active"] is True
    assert "id" in data
    assert "password_hash" not in data


def test_02_duplicate_registration(client):
    """2. Duplicate registration"""
    payload = {
        "email": "duplicate@example.com",
        "password": "SecurePassword123",
        "full_name": "User One"
    }
    res1 = client.post("/auth/register", json=payload)
    assert res1.status_code == 201

    res2 = client.post("/auth/register", json=payload)
    assert res2.status_code == 409
    assert "already registered" in res2.json()["detail"]


def test_03_successful_login(client):
    """3. Successful login"""
    # Register user first
    reg_payload = {
        "email": "loginuser@example.com",
        "password": "MySecretPassword123",
        "full_name": "Login User"
    }
    client.post("/auth/register", json=reg_payload)

    # Login
    login_payload = {
        "email": "loginuser@example.com",
        "password": "MySecretPassword123"
    }
    response = client.post("/auth/login", json=login_payload)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "loginuser@example.com"


def test_04_incorrect_password(client):
    """4. Incorrect password"""
    reg_payload = {
        "email": "wrongpwd@example.com",
        "password": "CorrectPassword123",
        "full_name": "Wrong Password Test"
    }
    client.post("/auth/register", json=reg_payload)

    login_payload = {
        "email": "wrongpwd@example.com",
        "password": "WrongPassword123"
    }
    response = client.post("/auth/login", json=login_payload)
    assert response.status_code == 401
    assert "Invalid email or password" in response.json()["detail"]


def test_05_unknown_email(client):
    """5. Unknown email"""
    login_payload = {
        "email": "nonexistent@example.com",
        "password": "SomePassword123"
    }
    response = client.post("/auth/login", json=login_payload)
    assert response.status_code == 401
    assert "Invalid email or password" in response.json()["detail"]


def test_06_inactive_user_login(client, db_session):
    """6. Inactive user login"""
    # Create inactive user directly in DB
    user = User(
        email="inactive@example.com",
        full_name="Inactive User",
        password_hash=hash_password("Password123"),
        role="student",
        is_active=False
    )
    db_session.add(user)
    db_session.commit()

    login_payload = {
        "email": "inactive@example.com",
        "password": "Password123"
    }
    response = client.post("/auth/login", json=login_payload)
    assert response.status_code == 403
    assert "inactive" in response.json()["detail"].lower()


def test_07_access_token_verification(client):
    """7. Access-token verification"""
    reg_payload = {
        "email": "verifyuser@example.com",
        "password": "Password123",
        "full_name": "Verify User"
    }
    client.post("/auth/register", json=reg_payload)
    login_res = client.post("/auth/login", json={"email": "verifyuser@example.com", "password": "Password123"})
    access_token = login_res.json()["access_token"]

    headers = {"Authorization": f"Bearer {access_token}"}
    me_res = client.get("/auth/me", headers=headers)
    assert me_res.status_code == 200
    assert me_res.json()["email"] == "verifyuser@example.com"


def test_08_expired_access_token(client):
    """8. Expired access token"""
    expired_token = create_access_token(
        user_id=999,
        email="expired@example.com",
        role="student",
        expires_delta=timedelta(seconds=-10)  # Already expired
    )
    headers = {"Authorization": f"Bearer {expired_token}"}
    response = client.get("/auth/me", headers=headers)
    assert response.status_code == 401
    assert "expired" in response.json()["detail"].lower() or "validate" in response.json()["detail"].lower()


def test_09_valid_refresh_token(client):
    """9. Valid refresh token"""
    reg_payload = {
        "email": "refreshuser@example.com",
        "password": "Password123",
        "full_name": "Refresh User"
    }
    client.post("/auth/register", json=reg_payload)
    login_res = client.post("/auth/login", json={"email": "refreshuser@example.com", "password": "Password123"})
    refresh_token = login_res.json()["refresh_token"]

    ref_res = client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert ref_res.status_code == 200
    assert "access_token" in ref_res.json()
    assert ref_res.json()["user"]["email"] == "refreshuser@example.com"


def test_10_invalid_refresh_token(client):
    """10. Invalid refresh token"""
    ref_res = client.post("/auth/refresh", json={"refresh_token": "invalid.garbage.token"})
    assert ref_res.status_code == 401


def test_11_revoked_refresh_token(client):
    """11. Revoked refresh token"""
    reg_payload = {
        "email": "revokeduser@example.com",
        "password": "Password123",
        "full_name": "Revoked User"
    }
    client.post("/auth/register", json=reg_payload)
    login_res = client.post("/auth/login", json={"email": "revokeduser@example.com", "password": "Password123"})
    refresh_token = login_res.json()["refresh_token"]

    # Logout to revoke refresh token
    logout_res = client.post("/auth/logout", json={"refresh_token": refresh_token})
    assert logout_res.status_code == 200

    # Attempt to refresh with revoked token
    ref_res = client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert ref_res.status_code == 401
    assert "revoked" in ref_res.json()["detail"].lower() or "inactive" in ref_res.json()["detail"].lower()


def test_12_logout(client):
    """12. Logout"""
    reg_payload = {
        "email": "logoutuser@example.com",
        "password": "Password123",
        "full_name": "Logout User"
    }
    client.post("/auth/register", json=reg_payload)
    login_res = client.post("/auth/login", json={"email": "logoutuser@example.com", "password": "Password123"})
    refresh_token = login_res.json()["refresh_token"]

    logout_res = client.post("/auth/logout", json={"refresh_token": refresh_token})
    assert logout_res.status_code == 200
    assert logout_res.json()["message"] == "Successfully logged out"


def test_13_password_reset_flow(client, db_session):
    """13. Password reset flow"""
    # Register user
    reg_payload = {
        "email": "resetpwd@example.com",
        "password": "OldPassword123",
        "full_name": "Reset Password User"
    }
    client.post("/auth/register", json=reg_payload)

    # Forgot password request
    forgot_res = client.post("/auth/forgot-password", json={"email": "resetpwd@example.com"})
    assert forgot_res.status_code == 200
    assert "password reset link" in forgot_res.json()["message"].lower()

    # Generate token manually to test reset-password endpoint
    from app.core.security import create_password_reset_token
    reset_token = create_password_reset_token("resetpwd@example.com")

    # Reset password
    reset_res = client.post("/auth/reset-password", json={
        "token": reset_token,
        "new_password": "NewPassword123"
    })
    assert reset_res.status_code == 200

    # Verify old password no longer works
    old_login = client.post("/auth/login", json={"email": "resetpwd@example.com", "password": "OldPassword123"})
    assert old_login.status_code == 401

    # Verify new password works
    new_login = client.post("/auth/login", json={"email": "resetpwd@example.com", "password": "NewPassword123"})
    assert new_login.status_code == 200
