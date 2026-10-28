from datetime import datetime, timezone
from typing import Optional
import uuid
from pydantic import BaseModel, Field


class AppointmentCreate(BaseModel):
    patient_id: str
    appointment_date: str = Field(..., description="Date of appointment e.g. YYYY-MM-DD or MM/DD/YYYY")
    appointment_time: str = Field(..., description="Time of appointment e.g. 10:00 AM")
    department: str = Field(default="General Practice", description="Clinic department or provider")
    reason: Optional[str] = Field(default="New Patient Initial Consultation")
    notes: Optional[str] = None


class AppointmentRecord(AppointmentCreate):
    appointment_id: str
    status: str = "Scheduled"
    created_at: str


class CallTranscriptCreate(BaseModel):
    call_id: Optional[str] = None
    patient_id: Optional[str] = None
    caller_phone: Optional[str] = None
    direction: str = "inbound"
    transcript: str
    summary: Optional[str] = None
    sentiment: Optional[str] = "neutral"
    duration_seconds: Optional[int] = 0
