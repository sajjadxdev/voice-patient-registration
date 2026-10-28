import pytest
from app.services.llm_agent import voice_agent, execute_agent_tool


def test_conversational_start_over():
    messages = [
        {"role": "assistant", "content": "Hi! Could I have your first and last name?"},
        {"role": "user", "content": "My name is John Doe"},
        {"role": "assistant", "content": "What is your date of birth?"},
        {"role": "user", "content": "Actually can we start over?"}
    ]
    res = voice_agent.process_turn(messages)
    assert res["is_completed"] is False
    assert "start fresh" in res["reply"].lower() or "beginning" in res["reply"].lower()


def test_conversational_spanish_switch():
    messages = [
        {"role": "assistant", "content": "Hi! Could I have your first and last name?"},
        {"role": "user", "content": "Hola, hablo español por favor"}
    ]
    res = voice_agent.process_turn(messages)
    assert res["is_completed"] is False
    # Check that reply contains Spanish words
    reply_lower = res["reply"].lower()
    assert any(w in reply_lower for w in ["nombre", "apellido", "registro", "desea", "claro"])


def test_conversational_duplicate_detection_prompt():
    # Jane Doe's phone is 415-555-0199
    messages = [
        {"role": "assistant", "content": "Could I have your first and last name?"},
        {"role": "user", "content": "Jane Doe"},
        {"role": "assistant", "content": "What is your date of birth?"},
        {"role": "user", "content": "05/12/1988"},
        {"role": "assistant", "content": "What is your phone number?"},
        {"role": "user", "content": "415-555-0199"}
    ]
    res = voice_agent.process_turn(messages)
    assert res["is_completed"] is False
    assert "already have a record for Jane Doe" in res["reply"]
    assert "update your information" in res["reply"]


def test_appointment_scheduling_bonus():
    # Schedule an appointment for seed patient Jane Doe
    from app.repositories.patient_repo import patient_repo
    jane = patient_repo.find_by_phone("415-555-0199")
    assert jane is not None
    
    appt_res = execute_agent_tool("schedule_appointment", {
        "patient_id": jane["patient_id"],
        "appointment_date": "2026-11-15",
        "appointment_time": "10:30 AM",
        "reason": "New Patient Physical Checkup"
    })
    assert appt_res["status"] == "success"
    assert "appointment_id" in appt_res

    # Check that the appointment is queryable
    appts = patient_repo.get_appointments_for_patient(jane["patient_id"])
    assert len(appts) >= 1
    assert appts[0]["appointment_time"] == "10:30 AM"
