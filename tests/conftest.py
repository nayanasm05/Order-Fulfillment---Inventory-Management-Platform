import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="session")
def client():
    return TestClient(app)


@pytest.fixture(scope="session")
def admin_token():
    return "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIyIiwicm9sZV9pZCI6MSwiZXhwIjoxNzkxNDc4Njg2LCJ0eXBlIjoiYWNjZXNzIn0.AkAXZz1ZUZyrUf2hr-yfylPMSGb_0rYqDdheDovWps0"


@pytest.fixture
def auth_headers(admin_token):
    return {
        "Authorization": f"Bearer {admin_token}"
    }