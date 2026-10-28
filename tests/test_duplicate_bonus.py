import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.llm_agent import execute_agent_tool

client = TestClient(app)


def test_duplicate_phone_recognition_via_api():
    # 1. Use seed patient Jane Doe's phone: 415-555-0199
    res = client.post("/patients/check-duplicate?phone_number=415-555-0199")
    assert res.status_code == 200
    body = res.json()["data"]
    assert body["is_duplicate"] is True
    assert body["patient"]["first_name"] == "Jane"
    assert body["patient"]["last_name"] == "Doe"
    assert "It looks like we already have a record" in body["message"]


def test_non_duplicate_phone_via_api():
    res = client.post("/patients/check-duplicate?phone_number=999-888-7777")
    assert res.status_code == 200
    body = res.json()["data"]
    assert body["is_duplicate"] is False
    assert body["patient"] is None


def test_agent_tool_check_patient_by_phone():
    tool_res = execute_agent_tool("check_patient_by_phone", {"phone_number": "(415) 555-0199"})
    assert tool_res["status"] == "exists"
    assert tool_res["first_name"] == "Jane"
