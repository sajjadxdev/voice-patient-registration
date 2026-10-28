import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import sqlite3

from app.database import get_db_cursor
from app.models.patient import PatientCreate, PatientUpdate, normalize_phone
from app.models.appointment import AppointmentCreate, CallTranscriptCreate


def row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    return dict(row)


class PatientRepository:
    def create(self, patient: PatientCreate) -> Dict[str, Any]:
        patient_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        
        with get_db_cursor() as cursor:
            cursor.execute("""
                INSERT INTO patients (
                    patient_id, first_name, last_name, date_of_birth, sex,
                    phone_number, email, address_line_1, address_line_2,
                    city, state, zip_code, insurance_provider, insurance_member_id,
                    preferred_language, emergency_contact_name, emergency_contact_phone,
                    created_at, updated_at, deleted_at
                ) VALUES (
                    ?, ?, ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?, ?, ?,
                    ?, ?, ?,
                    ?, ?, NULL
                )
            """, (
                patient_id,
                patient.first_name,
                patient.last_name,
                patient.date_of_birth,
                patient.sex.value if hasattr(patient.sex, "value") else str(patient.sex),
                patient.phone_number,
                patient.email,
                patient.address_line_1,
                patient.address_line_2,
                patient.city,
                patient.state,
                patient.zip_code,
                patient.insurance_provider,
                patient.insurance_member_id,
                patient.preferred_language or "English",
                patient.emergency_contact_name,
                patient.emergency_contact_phone,
                now,
                now
            ))
            
            cursor.execute("SELECT * FROM patients WHERE patient_id = ?", (patient_id,))
            row = cursor.fetchone()
            return row_to_dict(row)

    def get_by_id(self, patient_id: str, include_deleted: bool = False) -> Optional[Dict[str, Any]]:
        with get_db_cursor() as cursor:
            if include_deleted:
                cursor.execute("SELECT * FROM patients WHERE patient_id = ?", (patient_id,))
            else:
                cursor.execute("SELECT * FROM patients WHERE patient_id = ? AND deleted_at IS NULL", (patient_id,))
            row = cursor.fetchone()
            return row_to_dict(row) if row else None

    def find_by_phone(self, phone: str) -> Optional[Dict[str, Any]]:
        normalized = normalize_phone(phone)
        if not normalized:
            return None
        with get_db_cursor() as cursor:
            cursor.execute(
                "SELECT * FROM patients WHERE phone_number = ? AND deleted_at IS NULL ORDER BY created_at DESC LIMIT 1",
                (normalized,)
            )
            row = cursor.fetchone()
            return row_to_dict(row) if row else None

    def list(
        self,
        last_name: Optional[str] = None,
        date_of_birth: Optional[str] = None,
        phone_number: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        query = "SELECT * FROM patients WHERE deleted_at IS NULL"
        params: List[Any] = []

        if last_name:
            query += " AND LOWER(last_name) = LOWER(?)"
            params.append(last_name.strip())

        if date_of_birth:
            query += " AND date_of_birth = ?"
            params.append(date_of_birth.strip())

        if phone_number:
            try:
                norm_phone = normalize_phone(phone_number)
                query += " AND phone_number = ?"
                params.append(norm_phone)
            except ValueError:
                # If unparseable phone filter provided, fall back to matching as is
                query += " AND phone_number LIKE ?"
                params.append(f"%{phone_number.strip()}%")

        query += " ORDER BY created_at DESC"

        with get_db_cursor() as cursor:
            cursor.execute(query, tuple(params))
            rows = cursor.fetchall()
            return [row_to_dict(r) for r in rows]

    def update(self, patient_id: str, update_data: PatientUpdate) -> Optional[Dict[str, Any]]:
        fields_to_update = update_data.model_dump(exclude_unset=True)
        if not fields_to_update:
            return self.get_by_id(patient_id)

        # Convert enums if present
        if "sex" in fields_to_update and fields_to_update["sex"] is not None:
            fields_to_update["sex"] = fields_to_update["sex"].value if hasattr(fields_to_update["sex"], "value") else str(fields_to_update["sex"])

        fields_to_update["updated_at"] = datetime.now(timezone.utc).isoformat()

        clauses = []
        values = []
        for key, val in fields_to_update.items():
            clauses.append(f"{key} = ?")
            values.append(val)
        values.append(patient_id)

        sql = f"UPDATE patients SET {', '.join(clauses)} WHERE patient_id = ? AND deleted_at IS NULL"

        with get_db_cursor() as cursor:
            cursor.execute(sql, tuple(values))
            if cursor.rowcount == 0:
                return None
            cursor.execute("SELECT * FROM patients WHERE patient_id = ?", (patient_id,))
            row = cursor.fetchone()
            return row_to_dict(row) if row else None

    def soft_delete(self, patient_id: str) -> bool:
        now = datetime.now(timezone.utc).isoformat()
        with get_db_cursor() as cursor:
            cursor.execute(
                "UPDATE patients SET deleted_at = ?, updated_at = ? WHERE patient_id = ? AND deleted_at IS NULL",
                (now, now, patient_id)
            )
            return cursor.rowcount > 0

    # Appointment Bonus
    def create_appointment(self, appt: AppointmentCreate) -> Dict[str, Any]:
        appt_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        with get_db_cursor() as cursor:
            cursor.execute("""
                INSERT INTO appointments (
                    appointment_id, patient_id, appointment_date, appointment_time,
                    department, reason, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                appt_id,
                appt.patient_id,
                appt.appointment_date,
                appt.appointment_time,
                appt.department,
                appt.reason or "Initial Consultation",
                "Scheduled",
                now
            ))
            cursor.execute("SELECT * FROM appointments WHERE appointment_id = ?", (appt_id,))
            return row_to_dict(cursor.fetchone())

    def get_appointments_for_patient(self, patient_id: str) -> List[Dict[str, Any]]:
        with get_db_cursor() as cursor:
            cursor.execute("SELECT * FROM appointments WHERE patient_id = ? ORDER BY appointment_date ASC", (patient_id,))
            return [row_to_dict(r) for r in cursor.fetchall()]

    # Call Transcript Bonus
    def save_call_log(self, log: CallTranscriptCreate) -> Dict[str, Any]:
        call_id = log.call_id or str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        with get_db_cursor() as cursor:
            cursor.execute("""
                INSERT INTO call_logs (
                    call_id, patient_id, caller_phone, direction,
                    transcript, summary, sentiment, duration_seconds, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                call_id,
                log.patient_id,
                log.caller_phone,
                log.direction,
                log.transcript,
                log.summary,
                log.sentiment,
                log.duration_seconds,
                now
            ))
            cursor.execute("SELECT * FROM call_logs WHERE call_id = ?", (call_id,))
            return row_to_dict(cursor.fetchone())

    def list_call_logs(self, limit: int = 50) -> List[Dict[str, Any]]:
        with get_db_cursor() as cursor:
            cursor.execute("SELECT * FROM call_logs ORDER BY created_at DESC LIMIT ?", (limit,))
            return [row_to_dict(r) for r in cursor.fetchall()]


patient_repo = PatientRepository()
