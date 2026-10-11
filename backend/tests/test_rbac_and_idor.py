import pytest


@pytest.mark.asyncio
async def test_student_can_access_own_profile(client, student1_token):
    response = await client.get(
        "/api/v1/students/me",
        headers={"Authorization": f"Bearer {student1_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["tnea_application_number"] == "XYZ2026001"
    assert data["full_name"] == "Karthikeyan S"
    assert data["status"] == "ACTIVATED"


@pytest.mark.asyncio
async def test_student_can_access_own_admission(client, student1_token):
    response = await client.get(
        "/api/v1/students/me/admission",
        headers={"Authorization": f"Bearer {student1_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "app-001"
    assert data["status"] == "ACTIVATED"


@pytest.mark.asyncio
async def test_student_cannot_access_another_students_admission_idor(client, student1_token):
    # Student 1 attempts to access Student 2's admission (app-002)
    response = await client.get(
        "/api/v1/admissions/app-002",
        headers={"Authorization": f"Bearer {student1_token}"}
    )
    assert response.status_code == 403
    assert "Access forbidden" in response.json()["detail"]


@pytest.mark.asyncio
async def test_admin_can_access_any_students_admission(client, admin_token):
    # Admin can view Student 1's admission
    response1 = await client.get(
        "/api/v1/admissions/app-001",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response1.status_code == 200
    assert response1.json()["id"] == "app-001"

    # Admin can view Student 2's admission
    response2 = await client.get(
        "/api/v1/admissions/app-002",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response2.status_code == 200
    assert response2.json()["id"] == "app-002"


@pytest.mark.asyncio
async def test_student_cannot_access_admin_endpoints_rbac(client, student1_token):
    response = await client.get(
        "/api/v1/admin/dashboard",
        headers={"Authorization": f"Bearer {student1_token}"}
    )
    assert response.status_code == 403
    assert "forbidden" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_admin_can_access_admin_dashboard(client, admin_token):
    response = await client.get(
        "/api/v1/admin/dashboard",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["institution_name"] == "XYZ Engineering College"
    assert data["total_allotted"] >= 2
    assert "activated" in data
