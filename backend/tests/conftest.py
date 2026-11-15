import os
import tempfile

# Tests ALWAYS use their own database, never the one in your .env.
# Use TEST_DATABASE_URL to run them against PostgreSQL instead of SQLite.
_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL", f"sqlite:///{_tmp}/test.db")
os.environ["SECRET_KEY"] = "test-secret-key-test-secret-key-test-secret"
os.environ["UPLOAD_DIR"] = f"{_tmp}/uploads"
os.environ["AI_PROVIDER"] = "mock"

import pytest
from fastapi.testclient import TestClient

from app.core.database import Base, SessionLocal, engine
from app.core.security import hash_password
from app.main import app
from app.models.user import User, UserRole


@pytest.fixture(scope="session", autouse=True)
def _tables():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture(scope="session")
def client():
    return TestClient(app)


def _login(client, email):
    r = client.post("/auth/login", json={"email": email, "password": "password123"})
    assert r.status_code == 200, r.text
    return {"Authorization": "Bearer " + r.json()["access_token"]}


@pytest.fixture(scope="session")
def people(client):
    for kind, name, email in [
        ("patient", "Ramesh Patel", "p1@test.com"),
        ("patient", "Sita Devi", "p2@test.com"),
        ("healthcare-worker", "Dr Asha", "w@test.com"),
    ]:
        r = client.post(f"/auth/register/{kind}",
                        json={"full_name": name, "email": email, "password": "password123"})
        assert r.status_code == 201, r.text
    db = SessionLocal()
    db.add(User(full_name="Admin", email="a@test.com",
                hashed_password=hash_password("password123"), role=UserRole.ADMIN))
    db.commit()
    db.close()
    return {k: _login(client, f"{k}@test.com") for k in ["p1", "p2", "w", "a"]}
