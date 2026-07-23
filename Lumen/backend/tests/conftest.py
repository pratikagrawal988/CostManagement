"""
Shared pytest fixtures for the Lumen FinOps OS backend test suite.

Test isolation strategy: one shared SQLite file for the whole test session
(matches how `app.database` binds its engine at import time — swapping DBs
per-test would require re-patching every module that captured `SessionLocal`
at import time). Instead, each test gets a fresh, unique `tenant_id` via the
`tenant_id` fixture; since every model in this app is tenant-scoped and every
route filters by tenant_id, this gives full effective isolation without
touching shared/global tables.

Auth: requests are authenticated with real JWTs (via `auth_headers`/`auth`),
not the DEV_BYPASS_AUTH fallback — so RBAC enforcement is actually exercised
end-to-end, the same as it would be for a real client.
"""
from __future__ import annotations

import os
import uuid

# Must happen before any `app.*` module is imported anywhere in the test
# session — `app.database` binds its engine and `app.auth`/`app.crypto` read
# their secrets at *module import time*.
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_suite.db")
os.environ.setdefault("SCHEDULER_ENABLED", "false")
os.environ.setdefault("DEV_BYPASS_AUTH", "false")
os.environ.setdefault("SECRET_KEY", "pytest-only-test-secret-do-not-use-in-prod")
if not os.environ.get("SECRET_ENCRYPTION_KEY"):
    from cryptography.fernet import Fernet
    os.environ["SECRET_ENCRYPTION_KEY"] = Fernet.generate_key().decode()

import pytest
from fastapi.testclient import TestClient

from app.auth import create_access_token
from app.database import SessionLocal, create_all_tables
from app.models import Tenant


@pytest.fixture(scope="session", autouse=True)
def _init_db():
    """Create all tables once for the whole test session."""
    create_all_tables()
    yield


@pytest.fixture(scope="session")
def client():
    from app.main import app
    return TestClient(app)


@pytest.fixture()
def db():
    """Raw SQLAlchemy session for direct test setup/assertions."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def tenant_id(db):
    """A fresh, unique tenant per test — the isolation boundary for this suite."""
    tid = f"tenant-test-{uuid.uuid4().hex[:10]}"
    db.add(Tenant(id=tid, name="Test Tenant"))
    db.commit()
    return tid


def make_auth_headers(tenant_id: str, role: str = "admin", user_id: str | None = None, email: str | None = None) -> dict:
    token = create_access_token(
        user_id=user_id or f"user-{uuid.uuid4().hex[:8]}",
        tenant_id=tenant_id,
        email=email or "test@example.com",
        role=role,
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def auth(tenant_id):
    """`auth(role="admin")` -> Authorization header dict, bound to this test's tenant_id."""
    def _make(role: str = "admin"):
        return make_auth_headers(tenant_id, role=role)
    return _make
