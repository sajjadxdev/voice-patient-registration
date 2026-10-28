import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator
from app.config import settings

def get_db_path() -> str:
    db_path = Path(settings.DATABASE_PATH)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return str(db_path)


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(get_db_path(), timeout=10.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA busy_timeout = 5000;")
    return conn


@contextmanager
def get_db_cursor() -> Generator[sqlite3.Cursor, None, None]:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        yield cursor
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Initializes tables and indexes if they do not exist."""
    with get_db_cursor() as cursor:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS patients (
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
        """)
        
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_patients_phone ON patients(phone_number);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_patients_last_name ON patients(last_name);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_patients_dob ON patients(date_of_birth);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_patients_deleted ON patients(deleted_at);")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS appointments (
                appointment_id TEXT PRIMARY KEY,
                patient_id TEXT NOT NULL,
                appointment_date TEXT NOT NULL,
                appointment_time TEXT NOT NULL,
                department TEXT NOT NULL,
                reason TEXT,
                status TEXT DEFAULT 'Scheduled',
                created_at TEXT NOT NULL,
                FOREIGN KEY (patient_id) REFERENCES patients(patient_id)
            );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_appointments_patient ON appointments(patient_id);")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS call_logs (
                call_id TEXT PRIMARY KEY,
                patient_id TEXT,
                caller_phone TEXT,
                direction TEXT DEFAULT 'inbound',
                transcript TEXT NOT NULL,
                summary TEXT,
                sentiment TEXT DEFAULT 'neutral',
                duration_seconds INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                FOREIGN KEY (patient_id) REFERENCES patients(patient_id)
            );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_call_logs_patient ON call_logs(patient_id);")
