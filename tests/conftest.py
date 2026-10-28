import os
import pytest
from app.database import init_db
from app.services.seed_data import seed_patients_if_empty

@pytest.fixture(autouse=True, scope="session")
def setup_test_db():
    # Initialize schema and seed data for the test session
    init_db()
    seed_patients_if_empty()
    yield
