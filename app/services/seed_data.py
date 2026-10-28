import logging
from app.database import get_db_cursor
from app.repositories.patient_repo import patient_repo
from app.models.patient import PatientCreate, SexEnum

logger = logging.getLogger(__name__)

SEED_PATIENTS = [
    PatientCreate(
        first_name="Jane",
        last_name="Doe",
        date_of_birth="05/12/1988",
        sex=SexEnum.FEMALE,
        phone_number="415-555-0199",
        email="jane.doe@example.com",
        address_line_1="742 Evergreen Terrace",
        address_line_2="Apt 2B",
        city="Springfield",
        state="OR",
        zip_code="97477",
        insurance_provider="Blue Cross Blue Shield",
        insurance_member_id="BCBS-982314",
        preferred_language="English",
        emergency_contact_name="John Doe",
        emergency_contact_phone="415-555-0198"
    ),
    PatientCreate(
        first_name="Carlos",
        last_name="Santana",
        date_of_birth="08/24/1975",
        sex=SexEnum.MALE,
        phone_number="312-555-0144",
        email="carlos.santana@example.com",
        address_line_1="123 Michigan Ave",
        address_line_2=None,
        city="Chicago",
        state="IL",
        zip_code="60601",
        insurance_provider="Aetna Healthcare",
        insurance_member_id="AET-449120",
        preferred_language="Spanish",
        emergency_contact_name="Elena Santana",
        emergency_contact_phone="312-555-0145"
    )
]


def seed_patients_if_empty():
    """Seeds 1-2 initial records if the database is brand new."""
    with get_db_cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM patients")
        count = cursor.fetchone()[0]
        if count == 0:
            logger.info("Database is empty. Inserting seed patient records...")
            for seed in SEED_PATIENTS:
                patient_repo.create(seed)
            logger.info("Successfully seeded 2 demonstration patient records.")
