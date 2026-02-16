"""
Tests for auth API endpoints: registration with first/last name,
login, and profile retrieval.

Run: cd Platform/api && python -m pytest ../../tests/unit/test_auth_api.py -v
Or:  pytest tests/unit/test_auth_api.py -v  (from repo root with PYTHONPATH set)
"""
import sys
import os

# Add Platform/api to path so we can import app modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "Platform", "api"))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.db.session import get_db
from app.main import app


# In-memory SQLite for tests
TEST_DATABASE_URL = "sqlite:///./test_auth.db"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db():
    """Create tables before each test, drop after."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    # Clean up test db file
    try:
        os.remove("./test_auth.db")
    except OSError:
        pass


VALID_PAYLOAD = {
    "first_name": "John",
    "last_name": "Doe",
    "email": "john@example.com",
    "password": "StrongPass123!",
}


class TestRegister:
    def test_register_success(self):
        resp = client.post("/auth/register", json=VALID_PAYLOAD)
        assert resp.status_code == 200
        data = resp.json()
        assert data["first_name"] == "John"
        assert data["last_name"] == "Doe"
        assert data["email"] == "john@example.com"
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_register_fails_without_first_name(self):
        payload = {**VALID_PAYLOAD}
        del payload["first_name"]
        resp = client.post("/auth/register", json=payload)
        assert resp.status_code == 422

    def test_register_fails_without_last_name(self):
        payload = {**VALID_PAYLOAD}
        del payload["last_name"]
        resp = client.post("/auth/register", json=payload)
        assert resp.status_code == 422

    def test_register_fails_short_first_name(self):
        payload = {**VALID_PAYLOAD, "first_name": "J"}
        resp = client.post("/auth/register", json=payload)
        assert resp.status_code == 422

    def test_register_fails_short_password(self):
        payload = {**VALID_PAYLOAD, "password": "short"}
        resp = client.post("/auth/register", json=payload)
        assert resp.status_code == 422

    def test_register_fails_invalid_name_chars(self):
        payload = {**VALID_PAYLOAD, "first_name": "John123"}
        resp = client.post("/auth/register", json=payload)
        assert resp.status_code == 422

    def test_register_duplicate_email(self):
        client.post("/auth/register", json=VALID_PAYLOAD)
        resp = client.post("/auth/register", json=VALID_PAYLOAD)
        assert resp.status_code == 400
        assert "already registered" in resp.json()["detail"].lower()

    def test_register_allows_hyphenated_name(self):
        payload = {**VALID_PAYLOAD, "last_name": "O'Brien-Smith", "email": "obrien@example.com"}
        resp = client.post("/auth/register", json=payload)
        assert resp.status_code == 200
        assert resp.json()["last_name"] == "O'Brien-Smith"

    def test_register_normalizes_email(self):
        payload = {**VALID_PAYLOAD, "email": "JOHN@Example.COM"}
        resp = client.post("/auth/register", json=payload)
        assert resp.status_code == 200
        assert resp.json()["email"] == "john@example.com"


class TestLogin:
    def _register(self):
        client.post("/auth/register", json=VALID_PAYLOAD)

    def test_login_success(self):
        self._register()
        resp = client.post("/auth/login", json={
            "email": "john@example.com",
            "password": "StrongPass123!",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password(self):
        self._register()
        resp = client.post("/auth/login", json={
            "email": "john@example.com",
            "password": "WrongPassword1",
        })
        assert resp.status_code == 401

    def test_login_nonexistent_email(self):
        resp = client.post("/auth/login", json={
            "email": "nobody@example.com",
            "password": "StrongPass123!",
        })
        assert resp.status_code == 401


class TestProfile:
    def _register_and_get_token(self) -> str:
        resp = client.post("/auth/register", json=VALID_PAYLOAD)
        return resp.json()["access_token"]

    def test_profile_returns_name_fields(self):
        token = self._register_and_get_token()
        resp = client.get(
            "/api/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["first_name"] == "John"
        assert data["last_name"] == "Doe"
        assert data["full_name"] == "John Doe"
        assert data["email"] == "john@example.com"
        assert data["subscription_tier"] == "observer"

    def test_profile_requires_auth(self):
        resp = client.get("/api/me")
        assert resp.status_code in (401, 403)

    def test_profile_invalid_token(self):
        resp = client.get(
            "/api/me",
            headers={"Authorization": "Bearer invalid_token"},
        )
        assert resp.status_code == 401
