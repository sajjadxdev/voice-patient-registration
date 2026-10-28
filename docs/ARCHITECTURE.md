# System Architecture: Voice AI Patient Registration System

This document outlines the architectural design, separation of concerns, data pipelines, and error resilience strategies implemented for the Voice AI Patient Registration System at Oakwood Health Clinic.

---

## 1. High-Level Architecture Diagram

```mermaid
flowchart TB
    subgraph CallerChannel ["Caller Layer"]
        Caller["Dial-In Phone Caller\n(PSTN / Mobile)"]
        BrowserUser["Web Caller Simulator\n(Web Speech Mic / Audio)"]
    end

    subgraph TelephonyLayer ["Telephony & Voice AI Layer"]
        Vapi["Vapi / Retell AI\n(STT: Deepgram, TTS: ElevenLabs)"]
        Twilio["Twilio Voice Service\n(TwiML Gather & Voice Webhooks)"]
        WebSim["Browser Voice Agent Bridge\n(/voice/simulate/turn)"]
    end

    subgraph ServiceLayer ["Backend Application (FastAPI)"]
        RouterPatients["/patients Router\n(REST API CRUD & Envelope)"]
        RouterWebhooks["/voice Routers\n(Vapi & Twilio Webhooks)"]
        LLMAgent["VoiceAIAgent Engine\n(OpenAI / Gemini / Fallback State Machine)"]
        PatientService["Patient Service Layer\n(Validation, Duplicates, Appointments)"]
    end

    subgraph DataLayer ["Persistence Layer"]
        SQLite[("Persistent SQLite DB\n(WAL Mode, Foreign Keys, Indexes)")]
        TablePatients["patients table\n(Demographics, Soft-Delete)"]
        TableAppts["appointments table\n(Scheduled Visits)"]
        TableLogs["call_logs table\n(Transcripts, Sentiment)"]
    end

    Caller -->|PSTN SIP| Vapi
    Caller -->|PSTN Call| Twilio
    BrowserUser -->|HTTP / Audio| WebSim

    Vapi -->|POST Tool Calls| RouterWebhooks
    Twilio -->|POST TwiML Gather| RouterWebhooks
    WebSim -->|POST Session Turns| RouterWebhooks

    RouterWebhooks --> LLMAgent
    LLMAgent -->|Tool Calls| PatientService
    RouterPatients --> PatientService

    PatientService --> SQLite
    SQLite --> TablePatients
    SQLite --> TableAppts
    SQLite --> TableLogs
```

---

## 2. Separation of Concerns

The codebase follows a clean, modular tiered architecture:

| Layer | Directory / Module | Responsibility |
| :--- | :--- | :--- |
| **API Routers** | `app/routers/` | Exposes REST endpoints (`/patients`, `/voice/vapi`, `/voice/twilio`, `/voice/simulate`), validates request payloads, and formats uniform response envelopes. |
| **Service Layer** | `app/services/` | Contains core domain logic: caller duplicate detection, dynamic field normalization, appointment scheduling, and LLM prompt execution. |
| **LLM Agent** | `app/services/llm_agent.py` | Manages conversational state, prompt guidelines, confirmation read-backs, error re-prompting, multi-language switching, and function calling. |
| **Data Repositories** | `app/repositories/` | Direct database transactions, SQL parameterized queries, index usage, and soft-delete enforcement. |
| **Data Models** | `app/models/` | Strict Pydantic schemas enforcing standard U.S. patient demographic validation rules and consistent envelope structures. |
| **Database** | `app/database.py` | Connection pooling, SQLite WAL journal mode, automatic migrations, foreign key enforcement. |

---

## 3. End-to-End Call Sequence Flow

```mermaid
sequenceDiagram
    autonumber
    actor Caller
    participant Telephony as Telephony (Vapi / Twilio)
    participant Agent as LLM Voice Agent
    participant Service as Patient Service Layer
    participant DB as SQLite DB

    Caller->>Telephony: Inbound Phone Call
    Telephony->>Agent: Initiate Call / Greeting
    Agent->>Caller: "Hi! Thank you for calling Oakwood Health Clinic..."
    Caller->>Agent: "My name is Jane Doe, phone 415-555-0199"
    
    Agent->>Service: Tool: check_patient_by_phone("415-555-0199")
    Service->>DB: SELECT * FROM patients WHERE phone_number = ?
    DB-->>Service: Record Found!
    Service-->>Agent: { status: "exists", patient_id: "...", name: "Jane Doe" }
    
    Agent->>Caller: "It looks like we already have a record for Jane Doe. Would you like to update your information instead?"
    
    Note over Caller,Agent: Caller verifies details & provides new address
    
    Agent->>Caller: Mandatory Confirmation Read-Back:\n"Let me confirm everything I have: Jane Doe, DOB 05/12/1988..."
    Caller->>Agent: "Yes, that's correct."
    
    Agent->>Service: Tool: save_patient_registration(...)
    Service->>DB: INSERT INTO patients (...) VALUES (...)
    DB-->>Service: Patient Created (UUID)
    Service-->>Agent: { status: "success", patient_id: "uuid" }
    
    Agent->>Caller: "You're all set, Jane! Would you like to schedule your first appointment?"
    Caller->>Agent: "Yes, next Monday at 10 AM please."
    Agent->>Service: Tool: schedule_appointment(...)
    Service->>DB: INSERT INTO appointments (...)
    Agent->>Caller: "Your appointment is booked. Have a wonderful day! [Hangs up]"
    Telephony->>DB: Persist Call Transcript & Sentiment
```

---

## 4. Database Schema & Data Integrity

The SQLite database enforces referential integrity with `PRAGMA foreign_keys = ON;` and concurrency with `PRAGMA journal_mode = WAL;`.

### Patients Table (`patients`)
```sql
CREATE TABLE patients (
    patient_id TEXT PRIMARY KEY,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    date_of_birth TEXT NOT NULL,
    sex TEXT NOT NULL,
    phone_number TEXT NOT NULL,
    email TEXT,
    address_line_1 TEXT NOT NULL,
    address_line_2 TEXT,
    city TEXT NOT NULL,
    state TEXT NOT NULL,
    zip_code TEXT NOT NULL,
    insurance_provider TEXT,
    insurance_member_id TEXT,
    preferred_language TEXT DEFAULT 'English',
    emergency_contact_name TEXT,
    emergency_contact_phone TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT DEFAULT NULL
);
```

### Soft-Delete Pattern
Records are never permanently dropped from the database when `DELETE /patients/:id` is invoked. Instead, `deleted_at` is set to the current UTC timestamp. All `GET /patients` and `GET /patients/:id` queries filter `WHERE deleted_at IS NULL`.
