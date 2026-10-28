import pytest
from datetime import date, timedelta
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_list_patients_returns_standard_envelope():
    response = client.get("/patients")
    assert response.status_code == 200
    json_data = response.json()
    assert "data" in json_data
    assert "error" in json_data
    assert json_data["error"] is None
    assert isinstance(json_data["data"], list)


def test_create_patient_success():
    payload = {
        "first_name": "Alice",
        "last_name": "Smith",
        "date_of_birth": "04/20/1992",
        "sex": "Female",
        "phone_number": "503-555-8822",
        "email": "alice.smith@example.com",
        "address_line_1": "100 Pine Street",
        "city": "Seattle",
        "state": "WA",
        "zip_code": "98101",
        "insurance_provider": "Regence",
        "insurance_member_id": "REG-12345",
        "preferred_language": "English"
    }

    response = client.post("/patients", json=payload)
    assert response.status_code == 201
    body = response.json()
    assert body["error"] is None
    data = body["data"]
    assert data["first_name"] == "Alice"
    assert data["last_name"] == "Smith"
    assert data["patient_id"] is not None
    assert data["phone_number"] == "503-555-8822"
    assert data["deleted_at"] is None

    # Retrieve by ID
    get_res = client.get(f"/patients/{data['patient_id']}")
    assert get_res.status_code == 200
    assert get_res.json()["data"]["patient_id"] == data["patient_id"]


def test_create_patient_rejects_invalid_phone():
    payload = {
        "first_name": "Bob",
        "last_name": "Jones",
        "date_of_birth": "01/01/1985",
        "sex": "Male",
        "phone_number": "123",  # Invalid 3-digit phone
        "address_line_1": "123 Main St",
        "city": "Boise",
        "state": "ID",
        "zip_code": "83702"
    }

    response = client.post("/patients", json=payload)
    assert response.status_code in (400, 422)
    body = response.json()
    assert body["data"] is None
    assert body["error"] is not None


def test_create_patient_rejects_future_dob():
    future_dob = (date.today() + timedelta(days=365)).strftime("%m/%d/%Y")
    payload = {
        "first_name": "Future",
        "last_name": "Baby",
        "date_of_birth": future_dob,
        "sex": "Female",
        "phone_number": "503-555-9999",
        "address_line_1": "123 Main St",
        "city": "Boise",
        "state": "ID",
        "zip_code": "83702"
    }

    response = client.post("/patients", json=payload)
    assert response.status_code in (400, 422)
    body = response.json()
    assert body["data"] is None
    assert body["error"] is not None


def test_patient_query_params():
    # Filter by last_name
    res = client.get("/patients?last_name=Smith")
    assert res.status_code == 200
    assert all("smith" in p["last_name"].lower() for p in res.json()["data"])


def test_update_and_soft_delete_patient():
    # 1. Create a patient
    payload = {
        "first_name": "Charlie",
        "last_name": "Brown",
        "date_of_birth": "10/02/1950",
        "sex": "Male",
        "phone_number": "612-555-0101",
        "address_line_1": "720 Snoopy Lane",
        "city": "Minneapolis",
        "state": "MN",
        "zip_code": "55401"
    }
    create_res = client.post("/patients", json=payload)
    patient_id = create_res.json()["data"]["patient_id"]

    # 2. Update address
    update_res = client.put(f"/patients/{patient_id}", json={"address_line_1": "722 Snoopy Lane Apt 2"})
    assert update_res.status_code == 200
    assert update_res.json()["data"]["address_line_1"] == "722 Snoopy Lane Apt 2"

    # 3. Soft-delete
    del_res = client.delete(f"/patients/{patient_id}")
    assert del_res.status_code == 200
    assert del_res.json()["data"]["deleted"] is True

    # 4. Verify patient is no longer returned in GET /patients/:id
    get_after = client.get(f"/patients/{patient_id}")
    assert get_after.status_code == 404
    assert get_after.json()["error"]["code"] == 404
