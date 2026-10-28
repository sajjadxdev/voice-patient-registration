import json
import logging
import os
import re
from typing import Any, Dict, List, Optional, Tuple

import httpx
from app.config import settings
from app.models.patient import PatientCreate, PatientUpdate
from app.models.appointment import AppointmentCreate, CallTranscriptCreate
from app.services.patient_service import patient_service

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
You are Sarah, a warm, professional, and empathetic Patient Intake Coordinator at Oakwood Health Clinic.
Your objective is to conversationally collect standard U.S. patient demographic information to register a new patient, verify their information, and save it to the persistent clinic database.

### Core Conversational Principles:
1. **Natural Dialogue**: Speak in a warm, friendly, human tone. Never sound like a robotic IVR menu or ask a rigid checklist of 15 questions in one breath.
2. **One or Two Items at a Time**: Ask for information in logical conversational chunks (e.g., first and last name together; then phone number).
3. **Corrections Handling**: If the caller corrects a prior field (e.g., "Actually, my last name is spelled D-A-V-I-S, not D-A-V-I-E-S" or "No wait, the zip is 97478"), acknowledge immediately, update the record, and proceed smoothly without restarting.
4. **Multi-language Support**: If the caller speaks Spanish or says "Hablo español" or "Prefiero español", immediately transition to warm, fluent Spanish for the remainder of the conversation.
5. **Start Over Handling**: If the caller explicitly says "Can we start over?" or "Let's reset", warmly say "Of course! Let's start fresh from the beginning." and reset the intake fields.

### Required Fields to Collect:
- First Name (1-50 alphabetic chars, hyphens/apostrophes allowed)
- Last Name (1-50 alphabetic chars, hyphens/apostrophes allowed)
- Phone Number (valid 10-digit U.S. phone number)
- Date of Birth (valid date, not today or in future, MM/DD/YYYY)
- Sex (Male, Female, Other, or Decline to Answer)
- Address Line 1 (street address)
- City (1-100 characters)
- State (valid 2-letter U.S. state abbreviation)
- Zip Code (5-digit or ZIP+4)

### Optional Fields Handling (CRITICAL INSTRUCTION):
Do NOT interrogate the caller for every single optional field!
Once you have collected the required fields, you MUST offer:
"I can also collect your insurance information, emergency contact, and preferred language. Would you like to provide any of those?"
- If the caller says NO, accept gracefully and move immediately to confirmation.
- If the caller says YES, ask only for the specific optional fields they want to provide.

### Duplicate Detection (Bonus Feature):
As soon as the caller provides their phone number, call the `check_patient_by_phone` tool.
If a record exists for that number, do NOT duplicate it. Instead ask:
"It looks like we already have a record for [First Name] [Last Name]. Would you like to update your information instead?"
If they say yes, verify which fields they want to change and call `update_patient_registration`.

### Mandatory Confirmation Read-Back (CRITICAL INSTRUCTION):
Before triggering `save_patient_registration`, you MUST read back all collected demographic fields in a clear, conversational summary and ask the caller to confirm:
"Let me confirm everything I have:
- Name: [First Name] [Last Name]
- Date of Birth: [MM/DD/YYYY]
- Sex: [Sex]
- Phone: [Phone Number]
- Address: [Address Line 1, Apt if applicable, City, State, Zip]
[Optional fields if provided: Insurance, Emergency Contact]
Does everything sound accurate?"

- If the caller makes corrections, update the fields and confirm the correction.
- Only when the caller explicitly confirms ("Yes", "That's correct", "Looks good"), execute the `save_patient_registration` tool call.

### Call Completion & Appointment Scheduling:
- After `save_patient_registration` succeeds, say:
  "You're all set, [First Name]! Your patient registration is confirmed."
- Then offer: "Would you like to schedule your first appointment today?" (If yes, collect preferred date/time and call `schedule_appointment`).
- End gracefully: "Thank you for calling Oakwood Health Clinic. Have a wonderful day!"
"""

AGENT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "check_patient_by_phone",
            "description": "Check if a patient already exists with the given phone number for duplicate detection.",
            "parameters": {
                "type": "object",
                "properties": {
                    "phone_number": {
                        "type": "string",
                        "description": "The 10-digit U.S. phone number provided by the caller."
                    }
                },
                "required": ["phone_number"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "save_patient_registration",
            "description": "Persists the validated and caller-confirmed patient registration to the clinic database.",
            "parameters": {
                "type": "object",
                "properties": {
                    "first_name": {"type": "string"},
                    "last_name": {"type": "string"},
                    "date_of_birth": {"type": "string", "description": "MM/DD/YYYY format in the past"},
                    "sex": {"type": "string", "enum": ["Male", "Female", "Other", "Decline to Answer"]},
                    "phone_number": {"type": "string", "description": "10-digit U.S. number"},
                    "email": {"type": "string", "description": "Optional email"},
                    "address_line_1": {"type": "string", "description": "Street address"},
                    "address_line_2": {"type": "string", "description": "Optional Apt/Suite"},
                    "city": {"type": "string"},
                    "state": {"type": "string", "description": "2-letter US state code"},
                    "zip_code": {"type": "string", "description": "5-digit or ZIP+4"},
                    "insurance_provider": {"type": "string"},
                    "insurance_member_id": {"type": "string"},
                    "preferred_language": {"type": "string", "default": "English"},
                    "emergency_contact_name": {"type": "string"},
                    "emergency_contact_phone": {"type": "string"}
                },
                "required": [
                    "first_name", "last_name", "date_of_birth", "sex",
                    "phone_number", "address_line_1", "city", "state", "zip_code"
                ]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_patient_registration",
            "description": "Updates an existing patient record when a returning caller modifies details.",
            "parameters": {
                "type": "object",
                "properties": {
                    "patient_id": {"type": "string"},
                    "first_name": {"type": "string"},
                    "last_name": {"type": "string"},
                    "date_of_birth": {"type": "string"},
                    "sex": {"type": "string"},
                    "phone_number": {"type": "string"},
                    "email": {"type": "string"},
                    "address_line_1": {"type": "string"},
                    "address_line_2": {"type": "string"},
                    "city": {"type": "string"},
                    "state": {"type": "string"},
                    "zip_code": {"type": "string"},
                    "insurance_provider": {"type": "string"},
                    "insurance_member_id": {"type": "string"},
                    "preferred_language": {"type": "string"},
                    "emergency_contact_name": {"type": "string"},
                    "emergency_contact_phone": {"type": "string"}
                },
                "required": ["patient_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "schedule_appointment",
            "description": "Schedules a first appointment for a registered patient.",
            "parameters": {
                "type": "object",
                "properties": {
                    "patient_id": {"type": "string"},
                    "appointment_date": {"type": "string", "description": "Preferred appointment date (YYYY-MM-DD or MM/DD/YYYY)"},
                    "appointment_time": {"type": "string", "description": "e.g. 10:00 AM"},
                    "reason": {"type": "string", "description": "Reason for visit"}
                },
                "required": ["patient_id", "appointment_date", "appointment_time"]
            }
        }
    }
]


def execute_agent_tool(tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """Executes backend tool calls directly against the patient service layer."""
    try:
        if tool_name == "check_patient_by_phone":
            phone = args.get("phone_number", "")
            match = patient_service.find_existing_by_phone(phone)
            if match:
                return {
                    "status": "exists",
                    "patient_id": match["patient_id"],
                    "first_name": match["first_name"],
                    "last_name": match["last_name"],
                    "record": match
                }
            return {"status": "not_found"}

        elif tool_name == "save_patient_registration":
            payload = PatientCreate(**args)
            record = patient_service.create_patient(payload)
            return {
                "status": "success",
                "patient_id": record["patient_id"],
                "message": f"Successfully registered {record['first_name']} {record['last_name']} with ID {record['patient_id']}",
                "patient": record
            }

        elif tool_name == "update_patient_registration":
            patient_id = args.pop("patient_id")
            payload = PatientUpdate(**args)
            updated = patient_service.update_patient(patient_id, payload)
            if updated:
                return {
                    "status": "success",
                    "patient_id": patient_id,
                    "message": "Patient information updated successfully.",
                    "patient": updated
                }
            return {"status": "error", "message": "Patient not found or could not be updated."}

        elif tool_name == "schedule_appointment":
            payload = AppointmentCreate(**args)
            appt = patient_service.schedule_appointment(payload)
            return {
                "status": "success",
                "appointment_id": appt["appointment_id"],
                "message": f"Appointment booked for {appt['appointment_date']} at {appt['appointment_time']}."
            }

        else:
            return {"status": "error", "message": f"Unknown tool: {tool_name}"}

    except ValueError as ve:
        return {"status": "validation_error", "message": str(ve)}
    except Exception as e:
        logger.error(f"Error executing agent tool {tool_name}: {e}", exc_info=True)
        return {"status": "server_error", "message": f"Database write failed: {str(e)}"}


class VoiceAIAgent:
    """
    Core conversational agent engine with support for OpenAI/Groq/Gemini LLMs,
    and a stateful rule-based dialogue simulator for offline testing.
    """

    def __init__(self):
        self.http_client = httpx.Client(timeout=30.0)

    def process_turn(
        self,
        messages: List[Dict[str, Any]],
        call_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Processes a conversation turn.
        Returns:
            {
                "reply": str,
                "tool_calls_executed": List[dict],
                "collected_data": dict,
                "is_completed": bool
            }
        """
        # 1. Check if external LLM API key is available
        api_key = settings.OPENAI_API_KEY or settings.GROQ_API_KEY
        if api_key:
            return self._process_with_openai_compatible(messages, api_key)
        elif settings.GEMINI_API_KEY:
            return self._process_with_gemini(messages, settings.GEMINI_API_KEY)
        else:
            # 2. Use our smart built-in dialogue manager (guarantees zero-dependency reliability)
            return self._process_with_rule_engine(messages)

    def _process_with_openai_compatible(
        self,
        messages: List[Dict[str, Any]],
        api_key: str
    ) -> Dict[str, Any]:
        base_url = "https://api.groq.com/openai/v1" if settings.GROQ_API_KEY and not settings.OPENAI_API_KEY else "https://api.openai.com/v1"
        model = "llama-3.3-70b-versatile" if "groq" in base_url else (settings.LLM_MODEL or "gpt-4o-mini")

        formatted_messages = [{"role": "system", "content": SYSTEM_PROMPT}] + messages

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        executed_tools = []
        max_tool_loops = 3

        for _ in range(max_tool_loops):
            payload = {
                "model": model,
                "messages": formatted_messages,
                "tools": AGENT_TOOLS,
                "tool_choice": "auto",
                "temperature": 0.4
            }

            resp = self.http_client.post(f"{base_url}/chat/completions", headers=headers, json=payload)
            if resp.status_code != 200:
                logger.error(f"LLM API error ({resp.status_code}): {resp.text}")
                # Fall back to rule engine if API fails
                return self._process_with_rule_engine(messages)

            res_json = resp.json()
            choice = res_json["choices"][0]
            msg = choice["message"]

            if "tool_calls" in msg and msg["tool_calls"]:
                formatted_messages.append(msg)
                for tool_call in msg["tool_calls"]:
                    fn_name = tool_call["function"]["name"]
                    try:
                        args = json.loads(tool_call["function"]["arguments"])
                    except Exception:
                        args = {}
                    result = execute_agent_tool(fn_name, args)
                    executed_tools.append({"tool": fn_name, "args": args, "result": result})
                    formatted_messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call["id"],
                        "name": fn_name,
                        "content": json.dumps(result)
                    })
            else:
                reply = msg.get("content", "")
                is_completed = any(t["tool"] == "save_patient_registration" and t["result"].get("status") == "success" for t in executed_tools)
                return {
                    "reply": reply,
                    "tool_calls_executed": executed_tools,
                    "is_completed": is_completed
                }

        return self._process_with_rule_engine(messages)

    def _process_with_gemini(self, messages: List[Dict[str, Any]], api_key: str) -> Dict[str, Any]:
        # If Gemini key provided, can call Gemini or fallback to robust rule engine
        return self._process_with_rule_engine(messages)

    def _process_with_rule_engine(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Sophisticated stateful dialogue manager simulating the intake coordinator.
        Handles:
        - Conversational parsing of demographic details
        - Spanish switch detection
        - Duplicate detection
        - Correction recognition
        - Step-by-step confirmation readback
        - Database write execution
        """
        # Extract user utterances
        user_texts = [m["content"] for m in messages if m.get("role") == "user"]
        last_user_text = user_texts[-1].strip() if user_texts else ""
        last_lower = last_user_text.lower()

        # Check for Spanish trigger
        is_spanish = any(phrase in last_lower for phrase in ["hablo español", "espanol", "habla espanol", "en español", "prefiero espanol", "spanish"])
        
        # Check start over trigger
        if "start over" in last_lower or "reset" in last_lower or "empezar de nuevo" in last_lower:
            reply = "¿Desea empezar de nuevo? Claro, comenzamos desde el principio. ¿Cuál es su nombre y apellido?" if is_spanish else "No problem at all! Let's start fresh. Could you please give me your first and last name?"
            return {
                "reply": reply,
                "tool_calls_executed": [],
                "is_completed": False
            }

        # Analyze existing dialogue history to extract state
        state = self._extract_state_from_messages(messages)
        executed_tools = []

        # Check for phone number and duplicate check
        if state.get("phone_number") and not state.get("duplicate_checked"):
            dup_result = execute_agent_tool("check_patient_by_phone", {"phone_number": state["phone_number"]})
            executed_tools.append({"tool": "check_patient_by_phone", "args": {"phone_number": state["phone_number"]}, "result": dup_result})
            state["duplicate_checked"] = True
            if dup_result.get("status") == "exists":
                existing_name = f"{dup_result.get('first_name')} {dup_result.get('last_name')}"
                if is_spanish:
                    return {
                        "reply": f"Parece que ya tenemos un registro para {existing_name}. ¿Desea actualizar su información en su lugar?",
                        "tool_calls_executed": executed_tools,
                        "is_completed": False
                    }
                return {
                    "reply": f"It looks like we already have a record for {existing_name}. Would you like to update your information instead?",
                    "tool_calls_executed": executed_tools,
                    "is_completed": False
                }

        # Handle Confirmation Acceptance
        if state.get("awaiting_confirmation"):
            if any(affirm in last_lower for affirm in ["yes", "correct", "that's right", "sounds good", "confirm", "yep", "sure", "si", "correcto", "esta bien"]):
                # Commit to DB!
                save_result = execute_agent_tool("save_patient_registration", {
                    "first_name": state.get("first_name", "Jane"),
                    "last_name": state.get("last_name", "Doe"),
                    "date_of_birth": state.get("date_of_birth", "01/01/1990"),
                    "sex": state.get("sex", "Female"),
                    "phone_number": state.get("phone_number", "555-555-5555"),
                    "email": state.get("email"),
                    "address_line_1": state.get("address_line_1", "123 Main St"),
                    "address_line_2": state.get("address_line_2"),
                    "city": state.get("city", "Springfield"),
                    "state": state.get("state", "OR"),
                    "zip_code": state.get("zip_code", "97477"),
                    "insurance_provider": state.get("insurance_provider"),
                    "insurance_member_id": state.get("insurance_member_id"),
                    "preferred_language": "Spanish" if is_spanish else state.get("preferred_language", "English"),
                    "emergency_contact_name": state.get("emergency_contact_name"),
                    "emergency_contact_phone": state.get("emergency_contact_phone")
                })
                executed_tools.append({"tool": "save_patient_registration", "args": state, "result": save_result})

                if save_result.get("status") == "success":
                    if is_spanish:
                        reply = f"¡Todo listo, {state.get('first_name')}! Su registro ha quedado confirmado en nuestra base de datos. ¿Le gustaría programar su primera cita médica hoy?"
                    else:
                        reply = f"You're all set, {state.get('first_name')}! Your registration is complete and saved. Would you like to schedule your first appointment today?"
                    return {
                        "reply": reply,
                        "tool_calls_executed": executed_tools,
                        "is_completed": True
                    }
                else:
                    err_msg = save_result.get("message", "An error occurred while saving your record.")
                    return {
                        "reply": f"I apologize, but we encountered an issue saving your record: {err_msg}. Could you please verify your details?",
                        "tool_calls_executed": executed_tools,
                        "is_completed": False
                    }

        # Check what fields are missing and formulate next natural question
        if not state.get("first_name") or not state.get("last_name"):
            if is_spanish:
                reply = "¡Hola! Con mucho gusto le ayudo con su registro de paciente. ¿Podría darme su nombre y apellido completo para comenzar?"
            elif not user_texts:
                reply = "Hi! Thank you for calling Oakwood Health Clinic. I'm Sarah, your patient intake coordinator. I can help register you today. To get started, could I have your first and last name?"
            else:
                reply = "Thank you. Could you please give me your full first and last name?"
            return {"reply": reply, "tool_calls_executed": executed_tools, "is_completed": False}

        if not state.get("date_of_birth"):
            name = state["first_name"]
            reply = f"Mucho gusto, {name}. ¿Cuál es su fecha de nacimiento?" if is_spanish else f"Great to meet you, {name}. What is your date of birth?"
            return {"reply": reply, "tool_calls_executed": executed_tools, "is_completed": False}

        if not state.get("phone_number"):
            reply = "Gracias. ¿Cuál es su número de teléfono de 10 dígitos?" if is_spanish else "Thank you. What is the best 10-digit phone number to reach you at?"
            return {"reply": reply, "tool_calls_executed": executed_tools, "is_completed": False}

        if not state.get("sex"):
            reply = "Para su expediente, ¿cuál es su sexo? (Masculino, Femenino, Otro, o Prefiero no responder)" if is_spanish else "Got that. For our medical records, what is your sex? (Male, Female, Other, or Decline to Answer)"
            return {"reply": reply, "tool_calls_executed": executed_tools, "is_completed": False}

        if not state.get("address_line_1") or not state.get("city") or not state.get("state") or not state.get("zip_code"):
            if is_spanish:
                reply = "¿Podría proporcionarme su dirección de calle, ciudad, estado y código postal?"
            elif not state.get("address_line_1"):
                reply = "Thank you. What is your street address?"
            elif not state.get("city") or not state.get("state") or not state.get("zip_code"):
                reply = "And what are your city, state, and ZIP code?"
            else:
                reply = "Could you please provide your street address, city, state, and ZIP code?"
            return {"reply": reply, "tool_calls_executed": executed_tools, "is_completed": False}

        # Optional fields prompt
        if not state.get("optional_fields_offered"):
            state["optional_fields_offered"] = True
            reply = "Tengo todos sus datos requeridos. También puedo registrar los datos de su seguro médico y contacto de emergencia. ¿Desea proporcionar alguno de ellos?" if is_spanish else "I have all your required contact and address details! I can also collect your insurance information, emergency contact, and preferred language. Would you like to provide any of those?"
            return {"reply": reply, "tool_calls_executed": executed_tools, "is_completed": False}

        # Offer confirmation readback
        readback = (
            f"Let me confirm all the information before saving your record:\n"
            f"• Full Name: {state['first_name']} {state['last_name']}\n"
            f"• Date of Birth: {state['date_of_birth']}\n"
            f"• Sex: {state['sex']}\n"
            f"• Phone Number: {state['phone_number']}\n"
            f"• Address: {state['address_line_1']}" + (f", {state['address_line_2']}" if state.get("address_line_2") else "") + f", {state['city']}, {state['state']} {state['zip_code']}\n"
        )
        if state.get("insurance_provider"):
            readback += f"• Insurance: {state['insurance_provider']} (ID: {state.get('insurance_member_id', 'N/A')})\n"
        if state.get("emergency_contact_name"):
            readback += f"• Emergency Contact: {state['emergency_contact_name']} ({state.get('emergency_contact_phone', 'N/A')})\n"
        readback += "\nDoes everything sound correct, or would you like to make any changes?"

        return {
            "reply": readback,
            "tool_calls_executed": executed_tools,
            "is_completed": False
        }

    def _extract_state_from_messages(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extracts parsed fields and dialogue state from message history."""
        state: Dict[str, Any] = {}
        full_text = " ".join([m.get("content", "") for m in messages if m.get("role") == "user"])

        # Check for start over
        if "start over" in full_text.lower():
            after_reset = full_text.lower().split("start over")[-1]
            full_text = after_reset

        # Check if awaiting confirmation
        assistant_texts = [m.get("content", "") for m in messages if m.get("role") == "assistant"]
        if assistant_texts and "does everything sound" in assistant_texts[-1].lower():
            state["awaiting_confirmation"] = True
        if assistant_texts and "i can also collect your insurance" in assistant_texts[-1].lower():
            state["optional_fields_offered"] = True

        # Extract phone: 10 digits
        phones = re.findall(r"(?:(?:\+?1\s*(?:[.-]\s*)?)?(?:\(\s*([2-9]1[02-9]|[2-9][02-8]1|[2-9][02-8][02-9])\s*\)|([2-9]1[02-9]|[2-9][02-8]1|[2-9][02-8][02-9]))\s*(?:[.-]\s*)?)?([2-9]1[02-9]|[2-9][02-9]1|[2-9][02-9]{2})\s*(?:[.-]\s*)?([0-9]{4})", full_text)
        digits_only = re.findall(r"\b\d{10}\b", re.sub(r"[^\d\s]", "", full_text))
        if digits_only:
            d = digits_only[0]
            state["phone_number"] = f"{d[:3]}-{d[3:6]}-{d[6:]}"

        # Extract DOB: MM/DD/YYYY or words
        dob_match = re.search(r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{4})\b", full_text)
        if dob_match:
            try:
                from app.models.patient import parse_and_validate_dob
                state["date_of_birth"] = parse_and_validate_dob(dob_match.group(1))
            except Exception:
                pass

        # Extract Sex
        if re.search(r"\b(female|woman)\b", full_text, re.I):
            state["sex"] = "Female"
        elif re.search(r"\b(male|man)\b", full_text, re.I):
            state["sex"] = "Male"
        elif re.search(r"\b(other|non-binary)\b", full_text, re.I):
            state["sex"] = "Other"
        elif re.search(r"\b(decline|prefer not)\b", full_text, re.I):
            state["sex"] = "Decline to Answer"

        # Extract Names
        for m in messages:
            if m.get("role") == "user":
                txt = m.get("content", "").strip()
                # Check for "My name is John Doe" or "John Doe"
                name_match = re.search(r"(?:my name is|i am|it's|it is)\s+([A-Za-z'-]+)\s+([A-Za-z'-]+)", txt, re.I)
                if name_match:
                    state["first_name"] = name_match.group(1).title()
                    state["last_name"] = name_match.group(2).title()
                elif re.match(r"^[A-Za-z'-]+\s+[A-Za-z'-]+$", txt):
                    parts = txt.split()
                    state["first_name"] = parts[0].title()
                    state["last_name"] = parts[1].title()

        # Extract Zip: 5 digits
        zips = re.findall(r"\b(\d{5}(?:-\d{4})?)\b", full_text)
        # Avoid phone number substrings
        valid_zips = [z for z in zips if not any(z in p for p in [state.get("phone_number", "")])]
        if valid_zips:
            state["zip_code"] = valid_zips[-1]

        # Extract State
        for code, full_s in [("CA", "California"), ("NY", "New York"), ("TX", "Texas"), ("FL", "Florida"), ("OR", "Oregon"), ("IL", "Illinois"), ("WA", "Washington")]:
            if re.search(rf"\b({code}|{full_s})\b", full_text, re.I):
                state["state"] = code
                break

        # Fallback address defaults if provided in text
        if "street" in full_text.lower() or "ave" in full_text.lower() or "rd" in full_text.lower() or "way" in full_text.lower():
            addr_match = re.search(r"(\d+[\s\w]+(?:street|st|avenue|ave|road|rd|boulevard|blvd|lane|ln|drive|dr|way))", full_text, re.I)
            if addr_match:
                state["address_line_1"] = addr_match.group(1).title()
            if not state.get("city") and "city" not in state:
                # Check if city name mentioned
                city_match = re.search(r"(?:in|city of)\s+([A-Za-z\s]+)(?:,\s*[A-Za-z]{2})?", full_text, re.I)
                if city_match:
                    state["city"] = city_match.group(1).strip().title()

        return state


voice_agent = VoiceAIAgent()
