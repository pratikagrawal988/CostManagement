"""
Auth (register/login/refresh/me) and RBAC permission-matrix coverage.

RBAC is tested against the real permission matrix in app/rbac.py rather than
mocked, so a change to that matrix will break these tests if it silently
changes who can do what.
"""
from __future__ import annotations

import uuid

from app.rbac import PERMISSIONS, has_permission


# ── Auth flow ─────────────────────────────────────────────────────────────────

def test_register_then_me(client):
    email = f"user-{uuid.uuid4().hex[:8]}@example.com"
    r = client.post("/api/auth/register", json={
        "email": email, "password": "correct-horse-battery-staple", "full_name": "Test User",
    })
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["email"] == email
    assert body["role"] == "admin"  # first user in a new tenant is admin
    access_token = body["access_token"]

    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {access_token}"})
    assert me.status_code == 200, me.text
    assert me.json()["email"] == email


def test_login_wrong_password_rejected(client):
    email = f"user-{uuid.uuid4().hex[:8]}@example.com"
    client.post("/api/auth/register", json={"email": email, "password": "correct-password-123"})
    r = client.post("/api/auth/login", json={"email": email, "password": "wrong-password"})
    assert r.status_code == 401


def test_login_then_refresh_rotates_token(client):
    email = f"user-{uuid.uuid4().hex[:8]}@example.com"
    reg = client.post("/api/auth/register", json={"email": email, "password": "correct-password-123"}).json()

    login = client.post("/api/auth/login", json={"email": email, "password": "correct-password-123"})
    assert login.status_code == 200
    refresh_token = login.json()["refresh_token"]

    refreshed = client.post("/api/auth/refresh", json={"refresh_token": refresh_token})
    assert refreshed.status_code == 200, refreshed.text
    assert refreshed.json()["user_id"] == reg["user_id"]

    # Old refresh token is revoked after rotation — reusing it must fail.
    reused = client.post("/api/auth/refresh", json={"refresh_token": refresh_token})
    assert reused.status_code == 401


def test_me_requires_bearer_token(client):
    r = client.get("/api/auth/me")
    assert r.status_code == 401


# ── RBAC permission matrix ────────────────────────────────────────────────────

def test_permission_matrix_matches_expected_shape():
    """Guard against accidental widening/narrowing of the permission matrix."""
    assert has_permission("admin", "tags:write")
    assert has_permission("finops_engineer", "tags:write")
    assert not has_permission("analyst", "tags:write")
    assert not has_permission("viewer", "tags:write")

    assert has_permission("finance_manager", "budgets:write")
    assert not has_permission("finops_engineer", "budgets:write")
    assert not has_permission("team_lead", "budgets:write")

    assert has_permission("admin", "credentials:delete")
    assert not has_permission("finops_engineer", "credentials:delete")


def test_tags_read_endpoint_enforces_rbac(client, auth):
    # viewer is not in tags:read's role set -> 403
    r = client.get("/api/tags/policy", headers=auth("viewer"))
    assert r.status_code == 403

    # analyst is in tags:read but not tags:write
    r = client.get("/api/tags/policy", headers=auth("analyst"))
    assert r.status_code == 200

    r = client.put("/api/tags/policy", json={"required_keys": []}, headers=auth("analyst"))
    assert r.status_code == 403

    # admin can do both
    r = client.put("/api/tags/policy", json={"required_keys": []}, headers=auth("admin"))
    assert r.status_code == 200


def test_budgets_write_restricted_to_admin_and_finance_manager(client, auth):
    payload = {"name": "Test budget", "amount": 1000.0, "period": "monthly"}

    r = client.post("/api/budgets", json=payload, headers=auth("analyst"))
    assert r.status_code == 403

    r = client.post("/api/budgets", json=payload, headers=auth("finops_engineer"))
    assert r.status_code == 403

    r = client.post("/api/budgets", json=payload, headers=auth("finance_manager"))
    assert r.status_code == 201, r.text


def test_no_auth_header_rejected_on_protected_route(client):
    r = client.get("/api/tags/policy")
    assert r.status_code == 401


def test_permission_matrix_has_no_undefined_roles():
    """Every role referenced in the matrix must be a real, known role."""
    from app.rbac import ROLES
    known = set(ROLES.keys())
    for permission, roles in PERMISSIONS.items():
        unknown = roles - known
        assert not unknown, f"{permission} references unknown roles: {unknown}"
