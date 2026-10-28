import json
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_vapi_tool_calls_webhook():
    payload = {
        "message": {
            "type": "tool-calls",
            "toolCalls": [
                {
                    "id": "call_abc123",
                    "function": {
                        "name": "check_patient_by_phone",
                        "arguments": {
                            "phone_number": "415-555-0199"
                        }
                    }
                }
            ]
        }
    }

    response = client.post("/voice/vapi/webhook", json=payload)
    assert response.status_code == 200
    res_json = response.json()
    assert "results" in res_json
    assert len(res_json["results"]) == 1
    assert res_json["results"][0]["toolCallId"] == "call_abc123"
    result_data = json.loads(res_json["results"][0]["result"])
    assert result_data["status"] == "exists"
    assert result_data["first_name"] == "Jane"


def test_twilio_incoming_webhook():
    data = {
        "CallSid": "CA1234567890abcdef",
        "From": "+15035550199"
    }

    response = client.post("/voice/twilio/incoming", data=data)
    assert response.status_code == 200
    assert "application/xml" in response.headers["content-type"]
    assert "<Response>" in response.text
    assert "<Say" in response.text
    assert "<Gather" in response.text
