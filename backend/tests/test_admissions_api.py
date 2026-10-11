import pytest


@pytest.mark.asyncio
async def test_student_valid_transition(client, student1_token):
    # Student 1 transitions from ACTIVATED -> APPLICATION_IN_PROGRESS
    response = await client.post(
        "/api/v1/admissions/app-001/transition",
        headers={"Authorization": f"Bearer {student1_token}"},
        json={
            "target_state": "APPLICATION_IN_PROGRESS",
            "reason": "Candidate started filling digital form"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "APPLICATION_IN_PROGRESS"
    assert len(data["status_history"]) >= 1
    assert data["status_history"][0]["new_status"] == "APPLICATION_IN_PROGRESS"
    assert data["status_history"][0]["actor_role"] == "STUDENT"


@pytest.mark.asyncio
async def test_student_invalid_transition(client, student1_token):
    # Student 1 attempts invalid jump from ACTIVATED -> DOCUMENTS_VERIFIED
    response = await client.post(
        "/api/v1/admissions/app-001/transition",
        headers={"Authorization": f"Bearer {student1_token}"},
        json={"target_state": "DOCUMENTS_VERIFIED"}
    )
    assert response.status_code == 400
    assert "Invalid transition" in response.json()["detail"]


@pytest.mark.asyncio
async def test_admission_status_endpoint(client, student1_token):
    response = await client.get(
        "/api/v1/admissions/app-001/status",
        headers={"Authorization": f"Bearer {student1_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["current_status"] == "ACTIVATED"
    assert "APPLICATION_IN_PROGRESS" in data["allowed_next_states"]
