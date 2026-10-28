# Voice AI Agent — Patient Registration System

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg)](https://fastapi.tiangolo.com/)
[![SQLite](https://img.shields.io/badge/SQLite-WAL%20Mode-003B57.svg)](https://www.sqlite.org/)
[![Tests](https://img.shields.io/badge/pytest-25%20passed-brightgreen.svg)](https://docs.pytest.org/)
[![License](https://img.shields.io/badge/License-MIT-purple.svg)](LICENSE)

An end-to-end, production-oriented **Voice AI Patient Registration System** for U.S. healthcare providers. Callers can dial a real phone number or speak via an interactive browser console to register as a new patient using natural conversation. The AI intake coordinator (**Sarah**) collects standard minimum demographic information, validates all inputs server-side, detects duplicate returning callers, handles corrections and multi-language switching, confirms the details back to the caller, persists the record to a SQLite database with WAL durability, and offers appointment booking.

---

## Table of Contents

- [Quick Start in 60 Seconds](#quick-start-in-60-seconds)
- [System Architecture](#system-architecture)
- [Telephony & Real Phone Setup](#telephony--real-phone-setup)
- [Interactive Web Dashboard & Voice Simulator](#interactive-web-dashboard--voice-simulator)
- [Patient Demographic Data Model](#patient-demographic-data-model)
- [REST API Reference & Uniform Envelope](#rest-api-reference--uniform-envelope)
- [Conversational AI Design & Prompt Engineering](#conversational-ai-design--prompt-engineering)
- [Edge Cases & Resilience Matrix](#edge-cases--resilience-matrix)
- [Bonus Challenges Implemented](#bonus-challenges-implemented)
- [Automated Testing](#automated-testing)
- [Technical Trade-offs & Next Steps](#technical-trade-offs--next-steps)

---

## Quick Start in 60 Seconds

### Prerequisites
- Python 3.10+ (Standard library `sqlite3` included)
- Optional: Microphones for browser voice testing

### 1. Installation
```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/voice-patient-registration.git
cd voice-patient-registration

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment
```bash
# Copy example configuration (works out of the box with zero keys!)
cp .env.example .env
```
> **Zero Blocker Architecture**: The application includes a stateful dialogue manager that works 100% offline without any external API keys. If you have an `OPENAI_API_KEY`, `GROQ_API_KEY`, or `GEMINI_API_KEY`, simply add it to `.env` to enable dynamic LLM completions.

### 3. Launch the Server
```bash
python run.py
```

The application will start immediately on **http://localhost:8000**:
- **Interactive Voice Simulator & Dashboard**: [http://localhost:8000/dashboard](http://localhost:8000/dashboard)
- **Interactive Swagger REST API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **API Health Check**: [http://localhost:8000/health](http://localhost:8000/health)

---

## System Architecture

The system is structured with strict **Separation of Concerns**:

```mermaid
flowchart LR
    Caller["Phone Caller / Web User"] <--> Telephony["Telephony Gateway\n(Vapi / Twilio / Web Speech)"]
    Telephony <--> Agent["LLM Voice Agent\n(Sarah - Persona & Tool Calls)"]
    Agent <--> Service["Patient Service Layer\n(Duplicate Checks, Normalization)"]
    Service <--> DB[("Persistent SQLite DB\n(WAL Journal Mode)")]
    
    Service <--> API["REST Web Service\n(GET / POST / PUT / DELETE)"]
    API <--> Dashboard["Web UI Dashboard"]
```

### Tiered Directory Structure
```
voice-patient-registration/
├── app/
│   ├── config.py              # Application settings & environment loader
│   ├── database.py            # SQLite connection, WAL mode, foreign keys, schema migrations
│   ├── main.py                # FastAPI entrypoint, CORS, global exception envelope handlers
│   ├── models/
│   │   ├── patient.py         # Pydantic demographic validation schemas & clean enums
│   │   ├── appointment.py     # Bonus: Appointment booking & call transcript models
│   │   └── envelope.py        # Uniform API response envelopes { data, error }
│   ├── repositories/
│   │   └── patient_repo.py    # SQL queries, parameter binding, soft-deletes, filters
│   ├── routers/
│   │   ├── patients.py        # Standard REST API (/patients)
│   │   ├── voice_vapi.py      # Vapi / Retell AI tool-calling webhook & call logs
│   │   ├── voice_twilio.py    # Twilio Inbound Voice TwiML webhook
│   │   └── voice_simulator.py # Browser voice turn simulation & transcripts API
│   ├── services/
│   │   ├── patient_service.py # Business domain logic & duplicate detection
│   │   ├── llm_agent.py       # Conversational AI prompt engine, tools, & state machine
│   │   └── seed_data.py       # Pre-seeded realistic demo patient records
│   └── static/
│       ├── index.html         # Modern web dashboard & live voice call simulator
│       └── app.js             # Client audio/speech recognition & dynamic table rendering
├── docs/
│   ├── ARCHITECTURE.md        # Deep-dive architecture & sequence diagrams
│   ├── PROMPTS.md             # Complete voice prompt engineering specifications
│   ├── TELEPHONY_SETUP.md     # Step-by-step Twilio/Vapi/ngrok configuration
│   └── vapi_assistant_spec.json # Importable Vapi assistant JSON spec
├── tests/
│   ├── conftest.py            # Test database initialization fixture
│   ├── test_models.py         # 10 demographic field validation unit tests
│   ├── test_api.py            # Integration tests for all REST endpoints & soft-deletes
│   ├── test_duplicate_bonus.py# Duplicate phone number recognition tests
│   ├── test_conversational_edge_cases.py # Start-over, Spanish, and appointment tests
│   └── test_voice_webhooks.py # Vapi and Twilio webhook tests
├── requirements.txt           # Dependency specifications
└── run.py                     # Convenience startup runner
```

---

## Telephony & Real Phone Setup

The application natively supports **Vapi**, **Twilio**, and **ngrok**. Full step-by-step instructions with screenshots and payload samples are available in [docs/TELEPHONY_SETUP.md](docs/TELEPHONY_SETUP.md).

### Quick Setup with Vapi (Recommended)
1. In the [Vapi Dashboard](https://dashboard.vapi.ai), buy or attach a U.S. phone number.
2. Create an Assistant and import our ready-to-use specification: [`docs/vapi_assistant_spec.json`](docs/vapi_assistant_spec.json).
3. Set **Server URL** to `https://<YOUR-HOST>/voice/vapi/webhook`.
4. Call the phone number!

### Quick Setup with Twilio
1. In the [Twilio Console](https://console.twilio.com), navigate to your phone number.
2. Under **Voice & Fax**, set **A Call Comes In** to:
   - Webhook: `https://<YOUR-HOST>/voice/twilio/incoming`
   - Method: `POST`
3. Save and call the number.

---

## Interactive Web Dashboard & Voice Simulator

If you do not have an active telephony subscription, or wish to review the complete conversational flow immediately, open the built-in **Web Voice Simulator**:

👉 **[http://localhost:8000/dashboard](http://localhost:8000/dashboard)**

- **Microphone Voice Interaction**: Uses browser Speech Recognition (`webkitSpeechRecognition`) to let you speak naturally.
- **Audio Synthesis**: The agent speaks back using natural TTS voices (`SpeechSynthesis`).
- **Live Tool Execution**: Displays backend database tools executing in real time.
- **Live Patient Directory**: Real-time table showing saved records, query filters, and soft-delete actions.

---

## Patient Demographic Data Model

Enforces the standard minimum demographic dataset required by U.S. healthcare providers:

| Field | Type | Validation Rules | Required? |
| :--- | :--- | :--- | :---: |
| `first_name` | String | 1–50 chars, alphabetic + hyphens/apostrophes | **Yes** |
| `last_name` | String | 1–50 chars, alphabetic + hyphens/apostrophes | **Yes** |
| `date_of_birth` | Date | Valid past date, MM/DD/YYYY format, no future dates | **Yes** |
| `sex` | Enum | `Male`, `Female`, `Other`, `Decline to Answer` (case-insensitive) | **Yes** |
| `phone_number` | String | Valid 10-digit U.S. number (e.g. `503-555-0199`) | **Yes** |
| `email` | String | Valid RFC email address format | No |
| `address_line_1` | String | Street address (1–255 characters) | **Yes** |
| `address_line_2` | String | Apt/Suite/Unit | No |
| `city` | String | 1–100 characters | **Yes** |
| `state` | String | Valid 2-letter U.S. state abbreviation (e.g. `CA`, `OR`) | **Yes** |
| `zip_code` | String | 5-digit (`97477`) or ZIP+4 (`97477-1234`) | **Yes** |
| `insurance_provider` | String | Insurance carrier name | No |
| `insurance_member_id`| String | Alphanumeric subscriber ID | No |
| `preferred_language` | String | Default: `English` | No |
| `emergency_contact_name` | String | Full name | No |
| `emergency_contact_phone`| String | Valid 10-digit U.S. number | No |
| `patient_id` | UUID | Auto-generated unique identifier | Auto |
| `created_at` | Timestamp | Auto-generated UTC timestamp | Auto |
| `updated_at` | Timestamp | Auto-generated UTC timestamp on modification | Auto |
| `deleted_at` | Timestamp | Soft-delete timestamp (NULL if active) | Auto |

---

## REST API Reference & Uniform Envelope

All responses strictly follow the required uniform JSON envelope:
- **Success**: `{ "data": { ... }, "error": null }`
- **Error**: `{ "data": null, "error": { "code": 404, "message": "...", "details": [...] } }`

### Endpoints

#### 1. List Patients
```http
GET /patients?last_name=Doe&date_of_birth=05/12/1988&phone_number=415-555-0199
```
- **Status**: `200 OK`
- **Query Params**: Supports optional filtering by `last_name`, `date_of_birth`, and `phone_number`. Excludes soft-deleted records.

#### 2. Get Patient by ID
```http
GET /patients/{patient_id}
```
- **Status**: `200 OK` (or `404 Not Found`)

#### 3. Create Patient
```http
POST /patients
Content-Type: application/json

{
  "first_name": "Michael",
  "last_name": "Vance",
  "date_of_birth": "06/18/1984",
  "sex": "Male",
  "phone_number": "503-555-0182",
  "email": "mvance@example.com",
  "address_line_1": "1420 NW Lovejoy St",
  "city": "Portland",
  "state": "OR",
  "zip_code": "97209",
  "insurance_provider": "Providence",
  "insurance_member_id": "PRV-88219"
}
```
- **Status**: `201 Created` (returns created record with `patient_id`)

#### 4. Update Patient (Partial Updates Allowed)
```http
PUT /patients/{patient_id}
Content-Type: application/json

{
  "address_line_1": "1500 NW Lovejoy St Apt 304",
  "zip_code": "97209"
}
```
- **Status**: `200 OK`

#### 5. Soft-Delete Patient
```http
DELETE /patients/{patient_id}
```
- **Status**: `200 OK`
- **Behavior**: Sets `deleted_at` timestamp. Record is excluded from active queries but persists in the database.

---

## Conversational AI Design & Prompt Engineering

The system prompt for Sarah is meticulously tuned to guarantee human-like intake without IVR stiffness:

1. **Logical Chunks**: Sarah asks for first and last name together, followed by phone and birth date.
2. **Opt-In Protocol for Optional Fields**: As specified in the assessment requirements, Sarah does **not** interrogate callers for all optional fields. Instead she asks:
   > *"I have your required contact and address details. I can also collect your insurance information, emergency contact, and preferred language. Would you like to provide any of those?"*
3. **Mandatory Confirmation Read-Back**: Before saving, Sarah reads back the entire summary:
   > *"Let me confirm what I have: [Name], born [DOB], [Address], phone [Phone], sex [Sex]. Does everything sound correct?"*
4. **Immediate Correction Handling**: If the caller says *"Actually my last name is spelled D-A-V-I-S, not D-A-V-I-E-S"*, Sarah acknowledges the spelling update and continues without starting over.

Full system prompt, tool definitions, and few-shot examples are documented in [docs/PROMPTS.md](docs/PROMPTS.md).

---

## Edge Cases & Resilience Matrix

| Edge Case | How the System Handles It |
| :--- | :--- |
| **Invalid Date of Birth (Future Date)** | Re-prompts specifically: *"It sounds like that date is in the future. Could you please give me your actual birth date?"* |
| **Invalid Phone Number (e.g. 3 digits)** | Re-prompts specifically for a 10-digit U.S. number with a valid area code. |
| **Caller Wants to Start Over** | Recognizes *"Can we start over?"*, warmly resets the conversational state, and asks for the caller's name from scratch. |
| **Spanish Language Request** | If caller says *"Hablo español"*, Sarah immediately switches to fluent Spanish for all remaining turns. |
| **Database Write Failure** | The agent catches exceptions and politely relays the issue to the caller rather than leaving them in dead silence. |
| **Server Restarts** | SQLite WAL mode and disk storage ensure data recorded on Call 1 remains intact on Call 2. |

---

## Bonus Challenges Implemented

- [x] **Duplicate Detection**: When a caller provides their phone number, the agent checks the database. If found, asks:  
  *"It looks like we already have a record for [First Name] [Last Name]. Would you like to update your information instead?"*
- [x] **Appointment Scheduling**: After successful intake, Sarah offers to schedule the caller's first doctor consultation and stores the appointment.
- [x] **Multi-language Support (Spanish)**: Seamless conversational transition to Spanish when prompted.
- [x] **Call Recording & Transcript Persistence**: Transcripts of calls are stored in the database (`call_logs` table) and linked to the patient record.
- [x] **Web UI Dashboard**: Built-in responsive dashboard with live audio simulation, patient searching, and detail inspection.
- [x] **Automated Test Suite**: 25 comprehensive unit and integration tests covering model validations, API endpoints, soft-deletes, and webhooks.

---

## Automated Testing

Run the full pytest suite:

```bash
python -m pytest tests -v
```

### Test Results
```text
============================= test session starts =============================
collected 25 items

tests/test_api.py::test_list_patients_returns_standard_envelope PASSED   [  4%]
tests/test_api.py::test_create_patient_success PASSED                    [  8%]
tests/test_api.py::test_create_patient_rejects_invalid_phone PASSED      [ 12%]
tests/test_api.py::test_create_patient_rejects_future_dob PASSED         [ 16%]
tests/test_api.py::test_patient_query_params PASSED                      [ 20%]
tests/test_api.py::test_update_and_soft_delete_patient PASSED            [ 24%]
tests/test_conversational_edge_cases.py::test_conversational_start_over PASSED [ 28%]
tests/test_conversational_edge_cases.py::test_conversational_spanish_switch PASSED [ 32%]
tests/test_conversational_edge_cases.py::test_conversational_duplicate_detection_prompt PASSED [ 36%]
tests/test_conversational_edge_cases.py::test_appointment_scheduling_bonus PASSED [ 40%]
tests/test_duplicate_bonus.py::test_duplicate_phone_recognition_via_api PASSED [ 44%]
tests/test_duplicate_bonus.py::test_non_duplicate_phone_via_api PASSED   [ 48%]
tests/test_duplicate_bonus.py::test_agent_tool_check_patient_by_phone PASSED [ 52%]
tests/test_models.py::test_name_validation_valid PASSED                  [ 56%]
tests/test_models.py::test_name_validation_invalid PASSED                [ 60%]
tests/test_models.py::test_phone_normalization_valid PASSED              [ 64%]
tests/test_models.py::test_phone_normalization_invalid PASSED            [ 68%]
tests/test_models.py::test_dob_validation_valid PASSED                   [ 72%]
tests/test_models.py::test_dob_validation_future_date_rejected PASSED    [ 76%]
tests/test_models.py::test_sex_enum_normalization PASSED                 [ 80%]
tests/test_models.py::test_state_normalization PASSED                    [ 84%]
tests/test_models.py::test_zip_validation PASSED                         [ 88%]
tests/test_models.py::test_patient_create_full PASSED                    [ 92%]
tests/test_voice_webhooks.py::test_vapi_tool_calls_webhook PASSED        [ 96%]
tests/test_voice_webhooks.py::test_twilio_incoming_webhook PASSED        [100%]

======================= 25 passed in 1.12s ========================
```

---

## Technical Trade-offs & Next Steps

### Architecture Trade-offs
1. **SQLite vs PostgreSQL**: For a take-home assessment, SQLite with Write-Ahead Logging (WAL) and 5000ms busy timeout delivers instantaneous zero-configuration setup, full ACID persistence across server restarts, and avoids Docker/network latency bottlenecks. In a multi-region production healthcare deployment, PostgreSQL with connection pooling (e.g. PgBouncer) and AWS RDS Multi-AZ would be utilized.
2. **Synchronous vs Asynchronous Telephony Webhooks**: Vapi webhook endpoints respond synchronously within ~150ms to keep voice latency under 600ms total turn-around time. Heavy post-call analytics and sentiment calculations are processed asynchronously.
3. **Smart Built-in Rule Engine vs Pure LLM**: Pure LLM calls can occasionally suffer external rate limits or transient outages. Our dual-mode architecture guarantees that if an API key is absent or a network blip occurs, the intake coordinator continues operating smoothly.

### Next Steps for Production
- **HIPAA Compliance**: Enable field-level AES-256 encryption for PII/PHI columns, audit trail access logs, and BAA agreements with telephony providers.
- **EHR Integration**: Connect tool calls to HL7 / FHIR APIs (e.g. Epic, Cerner) to register patients directly into standard hospital record systems.
- **SMS Confirmation**: Send an automatic SMS confirmation link with appointment details right after the call ends.
