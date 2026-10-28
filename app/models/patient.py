import re
from datetime import date, datetime, timezone
from enum import Enum
from typing import Any, Optional
import uuid

from pydantic import BaseModel, Field, field_validator, model_validator


US_STATES = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas", "CA": "California",
    "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware", "FL": "Florida", "GA": "Georgia",
    "HI": "Hawaii", "ID": "Idaho", "IL": "Illinois", "IN": "Indiana", "IA": "Iowa",
    "KS": "Kansas", "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
    "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi", "MO": "Missouri",
    "MT": "Montana", "NE": "Nebraska", "NV": "Nevada", "NH": "New Hampshire", "NJ": "New Jersey",
    "NM": "New Mexico", "NY": "New York", "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio",
    "OK": "Oklahoma", "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina",
    "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah", "VT": "Vermont",
    "VA": "Virginia", "WA": "Washington", "WV": "West Virginia", "WI": "Wisconsin", "WY": "Wyoming",
    "DC": "District of Columbia", "PR": "Puerto Rico", "GU": "Guam", "VI": "Virgin Islands"
}

STATE_NAME_TO_CODE = {v.lower(): k for k, v in US_STATES.items()}
STATE_NAME_TO_CODE.update({k.lower(): k for k in US_STATES})


class SexEnum(str, Enum):
    MALE = "Male"
    FEMALE = "Female"
    OTHER = "Other"
    DECLINE_TO_ANSWER = "Decline to Answer"

    @classmethod
    def _missing_(cls, value: object):
        if isinstance(value, str):
            val_clean = value.strip().lower()
            if val_clean in ("male", "m", "man"):
                return cls.MALE
            if val_clean in ("female", "f", "woman"):
                return cls.FEMALE
            if val_clean in ("other", "o", "non-binary", "nonbinary"):
                return cls.OTHER
            if val_clean in ("decline to answer", "decline", "prefer not to say", "undisclosed"):
                return cls.DECLINE_TO_ANSWER
        return None


def clean_name(val: str, field_label: str) -> str:
    if not val:
        raise ValueError(f"{field_label} is required.")
    cleaned = val.strip()
    if len(cleaned) < 1 or len(cleaned) > 50:
        raise ValueError(f"{field_label} must be between 1 and 50 characters.")
    # Must be alphabetic with allowed hyphens and apostrophes
    if not re.match(r"^[A-Za-z]+([ '-][A-Za-z]+)*$", cleaned):
        raise ValueError(f"{field_label} may only contain alphabetic characters, hyphens, and apostrophes.")
    return cleaned


def normalize_phone(val: Optional[str], field_label: str = "Phone number") -> Optional[str]:
    if val is None or (isinstance(val, str) and not val.strip()):
        return None
    cleaned = re.sub(r"[^\d]", "", str(val))
    # Remove leading country code if 11 digits starting with 1
    if len(cleaned) == 11 and cleaned.startswith("1"):
        cleaned = cleaned[1:]
    if len(cleaned) != 10:
        raise ValueError(f"{field_label} must be a valid 10-digit U.S. number (received {val}).")
    if cleaned[0] in ("0", "1"):
        raise ValueError(f"{field_label} cannot have an area code starting with 0 or 1.")
    return f"{cleaned[:3]}-{cleaned[3:6]}-{cleaned[6:]}"


def parse_and_validate_dob(val: Any) -> str:
    if not val:
        raise ValueError("Date of birth is required.")
    
    parsed_date: Optional[date] = None
    if isinstance(val, date):
        parsed_date = val
    elif isinstance(val, str):
        val_str = val.strip()
        # Try MM/DD/YYYY
        for fmt in ("%m/%d/%Y", "%m-%d-%Y", "%Y-%m-%d", "%m/%d/%y"):
            try:
                parsed_date = datetime.strptime(val_str, fmt).date()
                break
            except ValueError:
                continue
    
    if parsed_date is None:
        raise ValueError("Invalid date of birth format. Expected MM/DD/YYYY.")
    
    today = date.today()
    if parsed_date >= today:
        raise ValueError("Date of birth cannot be today or in the future.")
    
    if parsed_date.year < 1900:
        raise ValueError("Date of birth year must be 1900 or later.")
    
    return parsed_date.strftime("%m/%d/%Y")


def validate_email_format(val: Optional[str]) -> Optional[str]:
    if not val or not str(val).strip():
        return None
    cleaned = str(val).strip().lower()
    email_regex = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    if not re.match(email_regex, cleaned):
        raise ValueError("Invalid email format.")
    return cleaned


def normalize_state(val: str) -> str:
    if not val:
        raise ValueError("State is required.")
    cleaned = val.strip().lower()
    if cleaned in STATE_NAME_TO_CODE:
        return STATE_NAME_TO_CODE[cleaned]
    if len(cleaned) == 2 and cleaned.upper() in US_STATES:
        return cleaned.upper()
    raise ValueError(f"'{val}' is not a valid 2-letter U.S. state abbreviation.")


def validate_zip_code(val: str) -> str:
    if not val:
        raise ValueError("ZIP code is required.")
    cleaned = val.strip()
    if not re.match(r"^\d{5}(-\d{4})?$", cleaned):
        raise ValueError("ZIP code must be 5 digits (e.g., 90210) or ZIP+4 (e.g., 90210-1234).")
    return cleaned


class PatientCreate(BaseModel):
    first_name: str = Field(..., description="First name, 1-50 alphabetic chars")
    last_name: str = Field(..., description="Last name, 1-50 alphabetic chars")
    date_of_birth: str = Field(..., description="Date of birth in MM/DD/YYYY format, past date")
    sex: SexEnum = Field(..., description="Biological sex or intake sex")
    phone_number: str = Field(..., description="10-digit U.S. phone number")
    email: Optional[str] = Field(None, description="Optional email address")
    address_line_1: str = Field(..., description="Street address")
    address_line_2: Optional[str] = Field(None, description="Apt, Suite, Unit if applicable")
    city: str = Field(..., description="City, 1-100 characters")
    state: str = Field(..., description="2-letter U.S. state abbreviation")
    zip_code: str = Field(..., description="5-digit or ZIP+4 format")
    insurance_provider: Optional[str] = Field(None, description="Insurance provider name")
    insurance_member_id: Optional[str] = Field(None, description="Insurance member/subscriber ID")
    preferred_language: str = Field(default="English", description="Preferred language (default English)")
    emergency_contact_name: Optional[str] = Field(None, description="Emergency contact full name")
    emergency_contact_phone: Optional[str] = Field(None, description="Emergency contact phone number")

    @field_validator("first_name")
    @classmethod
    def validate_first_name(cls, v: str) -> str:
        return clean_name(v, "First name")

    @field_validator("last_name")
    @classmethod
    def validate_last_name(cls, v: str) -> str:
        return clean_name(v, "Last name")

    @field_validator("date_of_birth")
    @classmethod
    def validate_dob(cls, v: Any) -> str:
        return parse_and_validate_dob(v)

    @field_validator("phone_number")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        res = normalize_phone(v, "Phone number")
        if not res:
            raise ValueError("Phone number is required.")
        return res

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        return validate_email_format(v)

    @field_validator("address_line_1")
    @classmethod
    def validate_address1(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Address line 1 is required.")
        cleaned = v.strip()
        if len(cleaned) > 255:
            raise ValueError("Address line 1 exceeds 255 characters.")
        return cleaned

    @field_validator("address_line_2")
    @classmethod
    def validate_address2(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        cleaned = v.strip()
        return cleaned if cleaned else None

    @field_validator("city")
    @classmethod
    def validate_city(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("City is required.")
        cleaned = v.strip()
        if len(cleaned) > 100:
            raise ValueError("City must be 100 characters or fewer.")
        return cleaned

    @field_validator("state")
    @classmethod
    def validate_state(cls, v: str) -> str:
        return normalize_state(v)

    @field_validator("zip_code")
    @classmethod
    def validate_zip(cls, v: str) -> str:
        return validate_zip_code(v)

    @field_validator("emergency_contact_phone")
    @classmethod
    def validate_emergency_phone(cls, v: Optional[str]) -> Optional[str]:
        return normalize_phone(v, "Emergency contact phone")


class PatientUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    date_of_birth: Optional[str] = None
    sex: Optional[SexEnum] = None
    phone_number: Optional[str] = None
    email: Optional[str] = None
    address_line_1: Optional[str] = None
    address_line_2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    insurance_provider: Optional[str] = None
    insurance_member_id: Optional[str] = None
    preferred_language: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None

    @field_validator("first_name")
    @classmethod
    def validate_first_name(cls, v: Optional[str]) -> Optional[str]:
        return clean_name(v, "First name") if v is not None else None

    @field_validator("last_name")
    @classmethod
    def validate_last_name(cls, v: Optional[str]) -> Optional[str]:
        return clean_name(v, "Last name") if v is not None else None

    @field_validator("date_of_birth")
    @classmethod
    def validate_dob(cls, v: Optional[Any]) -> Optional[str]:
        return parse_and_validate_dob(v) if v is not None else None

    @field_validator("phone_number")
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        return normalize_phone(v, "Phone number") if v is not None else None

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        return validate_email_format(v) if v is not None else None

    @field_validator("address_line_1")
    @classmethod
    def validate_address1(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            cleaned = v.strip()
            if not cleaned or len(cleaned) > 255:
                raise ValueError("Address line 1 must be between 1 and 255 characters.")
            return cleaned
        return None

    @field_validator("city")
    @classmethod
    def validate_city(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            cleaned = v.strip()
            if not cleaned or len(cleaned) > 100:
                raise ValueError("City must be between 1 and 100 characters.")
            return cleaned
        return None

    @field_validator("state")
    @classmethod
    def validate_state(cls, v: Optional[str]) -> Optional[str]:
        return normalize_state(v) if v is not None else None

    @field_validator("zip_code")
    @classmethod
    def validate_zip(cls, v: Optional[str]) -> Optional[str]:
        return validate_zip_code(v) if v is not None else None

    @field_validator("emergency_contact_phone")
    @classmethod
    def validate_emergency_phone(cls, v: Optional[str]) -> Optional[str]:
        return normalize_phone(v, "Emergency contact phone") if v is not None else None


class PatientRecord(PatientCreate):
    patient_id: str
    created_at: str
    updated_at: str
    deleted_at: Optional[str] = None
