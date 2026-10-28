import pytest
from datetime import date, timedelta
from app.models.patient import (
    PatientCreate, PatientUpdate, SexEnum,
    clean_name, normalize_phone, parse_and_validate_dob,
    normalize_state, validate_zip_code
)


def test_name_validation_valid():
    assert clean_name("John", "First name") == "John"
    assert clean_name("Mary-Jane", "First name") == "Mary-Jane"
    assert clean_name("O'Connor", "Last name") == "O'Connor"
    assert clean_name("Van Der Bilt", "Last name") == "Van Der Bilt"


def test_name_validation_invalid():
    with pytest.raises(ValueError, match="alphabetic"):
        clean_name("John123", "First name")
    with pytest.raises(ValueError, match="alphabetic"):
        clean_name("Jane@Doe", "Last name")
    with pytest.raises(ValueError, match="required"):
        clean_name("", "First name")


def test_phone_normalization_valid():
    assert normalize_phone("5551234567") == "555-123-4567"
    assert normalize_phone("(555) 123-4567") == "555-123-4567"
    assert normalize_phone("+1 555-123-4567") == "555-123-4567"
    assert normalize_phone("15551234567") == "555-123-4567"


def test_phone_normalization_invalid():
    with pytest.raises(ValueError, match="valid 10-digit"):
        normalize_phone("123")  # 3-digit phone from assessment prompt
    with pytest.raises(ValueError, match="area code starting with 0 or 1"):
        normalize_phone("012-345-6789")


def test_dob_validation_valid():
    assert parse_and_validate_dob("05/12/1988") == "05/12/1988"
    assert parse_and_validate_dob("1995-10-25") == "10/25/1995"


def test_dob_validation_future_date_rejected():
    future_date = (date.today() + timedelta(days=365)).strftime("%m/%d/%Y")
    with pytest.raises(ValueError, match="cannot be today or in the future"):
        parse_and_validate_dob(future_date)


def test_sex_enum_normalization():
    assert SexEnum("Male") == SexEnum.MALE
    assert SexEnum("female") == SexEnum.FEMALE
    assert SexEnum("Decline to Answer") == SexEnum.DECLINE_TO_ANSWER
    assert SexEnum("nonbinary") == SexEnum.OTHER


def test_state_normalization():
    assert normalize_state("CA") == "CA"
    assert normalize_state("ca") == "CA"
    assert normalize_state("California") == "CA"
    assert normalize_state("New York") == "NY"
    with pytest.raises(ValueError):
        normalize_state("InvalidState")


def test_zip_validation():
    assert validate_zip_code("90210") == "90210"
    assert validate_zip_code("90210-1234") == "90210-1234"
    with pytest.raises(ValueError):
        validate_zip_code("9021")
    with pytest.raises(ValueError):
        validate_zip_code("ABCDE")


def test_patient_create_full():
    patient = PatientCreate(
        first_name="Robert",
        last_name="Johnson",
        date_of_birth="03/15/1980",
        sex=SexEnum.MALE,
        phone_number="(503) 555-0192",
        email="robert.j@example.com",
        address_line_1="456 Oak Avenue",
        city="Portland",
        state="Oregon",
        zip_code="97201"
    )
    assert patient.first_name == "Robert"
    assert patient.state == "OR"
    assert patient.phone_number == "503-555-0192"
    assert patient.preferred_language == "English"
