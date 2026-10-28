import logging
from typing import Any, Dict, List, Optional, Tuple
from app.models.patient import (
    PatientCreate, PatientUpdate, normalize_phone,
    clean_name, parse_and_validate_dob, SexEnum, normalize_state, validate_zip_code
)
from app.models.appointment import AppointmentCreate, CallTranscriptCreate
from app.repositories.patient_repo import patient_repo

logger = logging.getLogger(__name__)


class PatientService:
    def create_patient(self, data: PatientCreate) -> Dict[str, Any]:
        """Creates a new patient record in the persistent database."""
        logger.info(f"Creating patient record for: {data.first_name} {data.last_name}")
        return patient_repo.create(data)

    def get_patient_by_id(self, patient_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves an active patient by their UUID."""
        return patient_repo.get_by_id(patient_id)

    def find_existing_by_phone(self, phone: str) -> Optional[Dict[str, Any]]:
        """Finds active patient by phone number for duplicate detection bonus."""
        try:
            return patient_repo.find_by_phone(phone)
        except Exception as e:
            logger.warning(f"Error checking duplicate phone '{phone}': {e}")
            return None

    def list_patients(
        self,
        last_name: Optional[str] = None,
        date_of_birth: Optional[str] = None,
        phone_number: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Lists active patients with optional query parameter filters."""
        return patient_repo.list(last_name=last_name, date_of_birth=date_of_birth, phone_number=phone_number)

    def update_patient(self, patient_id: str, updates: PatientUpdate) -> Optional[Dict[str, Any]]:
        """Partially updates an active patient record."""
        logger.info(f"Updating patient ID {patient_id}")
        return patient_repo.update(patient_id, updates)

    def soft_delete_patient(self, patient_id: str) -> bool:
        """Soft-deletes a patient record (sets deleted_at timestamp)."""
        logger.info(f"Soft-deleting patient ID {patient_id}")
        return patient_repo.soft_delete(patient_id)

    def validate_single_field(self, field_name: str, value: Any) -> Tuple[bool, Optional[str], Optional[Any]]:
        """
        Validates an individual field dynamically during conversational intake.
        Returns: (is_valid, error_message, normalized_value)
        """
        try:
            field = field_name.strip().lower()
            if field in ("first_name", "first name", "firstname"):
                norm = clean_name(str(value), "First name")
                return True, None, norm
            elif field in ("last_name", "last name", "lastname"):
                norm = clean_name(str(value), "Last name")
                return True, None, norm
            elif field in ("date_of_birth", "dob", "birthdate"):
                norm = parse_and_validate_dob(value)
                return True, None, norm
            elif field in ("sex", "gender"):
                norm_sex = SexEnum(value)
                return True, None, norm_sex.value
            elif field in ("phone_number", "phone", "telephone"):
                norm = normalize_phone(str(value), "Phone number")
                return True, None, norm
            elif field in ("state",):
                norm = normalize_state(str(value))
                return True, None, norm
            elif field in ("zip_code", "zip", "postal_code"):
                norm = validate_zip_code(str(value))
                return True, None, norm
            else:
                return True, None, value
        except Exception as e:
            return False, str(e), None

    def schedule_appointment(self, appt: AppointmentCreate) -> Dict[str, Any]:
        """Schedules a first appointment for a registered patient."""
        return patient_repo.create_appointment(appt)

    def record_call_transcript(self, transcript_data: CallTranscriptCreate) -> Dict[str, Any]:
        """Stores a call transcript / summary in the database."""
        return patient_repo.save_call_log(transcript_data)


patient_service = PatientService()
