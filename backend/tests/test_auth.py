import pytest
from app.core.security import verify_password, get_password_hash, decode_access_token


def test_password_hashing():
    raw_pwd = "StrongSecurePassword@2026"
    pwd_hash = get_password_hash(raw_pwd)
    
    assert pwd_hash != raw_pwd
    assert verify_password(raw_pwd, pwd_hash) is True
    assert verify_password("WrongPassword", pwd_hash) is False


@pytest.mark.asyncio
async def test_login_success(client):
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "karthik.xyz2026001@demo.admissionai.local", "password": "Student@1234"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["role"] == "STUDENT"
    assert data["email"] == "karthik.xyz2026001@demo.admissionai.local"

    # Validate payload
    payload = decode_access_token(data["access_token"])
    assert payload is not None
    assert payload["role"] == "STUDENT"
    assert payload["email"] == "karthik.xyz2026001@demo.admissionai.local"


@pytest.mark.asyncio
async def test_login_failure_wrong_password(client):
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "karthik.xyz2026001@demo.admissionai.local", "password": "WrongPassword@999"}
    )
    assert response.status_code == 401
    assert "detail" in response.json()


@pytest.mark.asyncio
async def test_login_failure_nonexistent_user(client):
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "nonexistent@demo.admissionai.local", "password": "Password@123"}
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_me_authenticated(client, student1_token):
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {student1_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "karthik.xyz2026001@demo.admissionai.local"
    assert data["role"] == "STUDENT"
    assert data["student_id"] == "student-001"
    assert data["institution_name"] == "XYZ Engineering College"


@pytest.mark.asyncio
async def test_get_me_unauthorized(client):
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401
