import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse

from app.models.patient import PatientCreate, PatientUpdate
from app.models.appointment import AppointmentCreate
from app.models.envelope import api_success, api_error
from app.services.patient_service import patient_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/patients", tags=["Patients"])


@router.get("", status_code=status.HTTP_200_OK)
def list_patients(
    last_name: Optional[str] = Query(None, description="Filter by patient last name"),
    date_of_birth: Optional[str] = Query(None, description="Filter by date of birth (MM/DD/YYYY)"),
    phone_number: Optional[str] = Query(None, description="Filter by phone number (e.g. 555-123-4567)")
):
    """
    List all active patients. Supports optional query filters:
    ?last_name=, ?date_of_birth=, ?phone_number=
    """
    try:
        patients = patient_service.list_patients(
            last_name=last_name,
            date_of_birth=date_of_birth,
            phone_number=phone_number
        )
        return api_success(patients)
    except Exception as e:
        logger.error(f"Error listing patients: {e}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=api_error("Internal server error retrieving patient list", code=500, details=str(e))
        )


@router.get("/{patient_id}", status_code=status.HTTP_200_OK)
def get_patient(patient_id: str):
    """
    Retrieve a single active patient by patient_id (UUID).
    """
    patient = patient_service.get_patient_by_id(patient_id)
    if not patient:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=api_error(f"Patient with ID '{patient_id}' not found.", code=404)
        )
    return api_success(patient)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_patient(payload: PatientCreate):
    """
    Create a new patient with full server-side validation.
    Returns the created record with patient_id.
    """
    try:
        created = patient_service.create_patient(payload)
        return api_success(created)
    except ValueError as ve:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=api_error(str(ve), code=400)
        )
    except Exception as e:
        logger.error(f"Error creating patient: {e}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=api_error("Database failure while creating patient.", code=500, details=str(e))
        )


@router.put("/{patient_id}", status_code=status.HTTP_200_OK)
def update_patient(patient_id: str, payload: PatientUpdate):
    """
    Update an existing patient record. Partial updates allowed.
    """
    # Check if patient exists first
    existing = patient_service.get_patient_by_id(patient_id)
    if not existing:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=api_error(f"Patient with ID '{patient_id}' not found.", code=404)
        )

    try:
        updated = patient_service.update_patient(patient_id, payload)
        if not updated:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content=api_error(f"Patient with ID '{patient_id}' could not be updated.", code=404)
            )
        return api_success(updated)
    except ValueError as ve:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=api_error(str(ve), code=400)
        )
    except Exception as e:
        logger.error(f"Error updating patient {patient_id}: {e}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=api_error("Failed to update patient record.", code=500, details=str(e))
        )


@router.delete("/{patient_id}", status_code=status.HTTP_200_OK)
def delete_patient(patient_id: str):
    """
    Soft-delete a patient record (sets deleted_at timestamp; does not hard-delete).
    """
    success = patient_service.soft_delete_patient(patient_id)
    if not success:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=api_error(f"Patient with ID '{patient_id}' not found or already deleted.", code=404)
        )
    return api_success({"patient_id": patient_id, "deleted": True, "message": "Patient successfully soft-deleted."})


# Bonus Endpoints
@router.post("/check-duplicate", status_code=status.HTTP_200_OK)
def check_duplicate(phone_number: str = Query(..., description="Phone number to check")):
    """
    Duplicate Detection Bonus: Check if caller phone matches an existing patient.
    """
    existing = patient_service.find_existing_by_phone(phone_number)
    if existing:
        return api_success({
            "is_duplicate": True,
            "patient": existing,
            "message": f"It looks like we already have a record for {existing['first_name']} {existing['last_name']}."
        })
    return api_success({"is_duplicate": False, "patient": None})


@router.post("/{patient_id}/appointments", status_code=status.HTTP_201_CREATED)
def schedule_appointment(patient_id: str, payload: AppointmentCreate):
    """
    Bonus: Schedule first appointment for a registered patient.
    """
    existing = patient_service.get_patient_by_id(patient_id)
    if not existing:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=api_error(f"Patient with ID '{patient_id}' not found.", code=404)
        )
    payload.patient_id = patient_id
    appt = patient_service.schedule_appointment(payload)
    return api_success(appt)
