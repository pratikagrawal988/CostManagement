"""
Coverage for credential encryption at rest (crypto.py) and the credential
management API (routes_credentials.py).

The key thing being pinned down: client_secret / service_account_json must
never be stored in plaintext, must round-trip correctly through encrypt/
decrypt, and must be stored under the exact JSON key
(`encrypted_secret` / `encrypted_sa_json`) that azure_jobs.py / gcp_jobs.py
read back out at ingestion time — a mismatch here silently breaks live
scheduled ingestion (this happened once already this project; see
AzureCostIngestConfig/GcpCostIngestConfig fixes).
"""
from __future__ import annotations

from app.crypto import decrypt_secret, encrypt_secret, is_encrypted
from app.models import AzureCostIngestConfig, GcpCostIngestConfig


# ── crypto.py unit coverage ────────────────────────────────────────────────────

def test_encrypt_decrypt_round_trip():
    secret = "super-secret-client-secret-value"
    ct = encrypt_secret(secret)
    assert ct != secret
    assert ct.startswith("v1:")
    assert is_encrypted(ct)
    assert decrypt_secret(ct) == secret


def test_encrypt_empty_string_returns_empty():
    assert encrypt_secret("") == ""
    assert decrypt_secret("") == ""


def test_legacy_plain_base64_still_decrypts():
    import base64
    legacy = base64.b64encode(b"old-style-secret").decode()
    assert not is_encrypted(legacy)
    assert decrypt_secret(legacy) == "old-style-secret"


# ── routes_credentials.py: Azure ──────────────────────────────────────────────

def test_azure_credential_stores_encrypted_not_plaintext(client, auth, db, tenant_id):
    secret = "azure-sp-secret-abc123"
    r = client.post("/api/credentials/azure", headers=auth("admin"), json={
        "tenant_id": tenant_id, "azure_tenant_id": "aad-tenant-1", "client_id": "client-1",
        "client_secret": secret, "subscription_id": "sub-1",
    })
    assert r.status_code == 200, r.text

    row = db.query(AzureCostIngestConfig).filter(AzureCostIngestConfig.tenant_id == tenant_id).one()
    stored = row.config.get("encrypted_secret", "")
    assert stored and stored != secret
    assert secret not in str(row.config)          # plaintext never persisted
    assert decrypt_secret(stored) == secret        # round-trips correctly

    # List endpoint must never leak the secret either
    listed = client.get("/api/credentials", headers=auth("analyst"), params={"tenant_id": tenant_id})
    assert secret not in listed.text


def test_gcp_credential_stores_encrypted_not_plaintext(client, auth, db, tenant_id):
    sa_json = '{"type": "service_account", "private_key": "-----BEGIN PRIVATE KEY-----FAKE-----END PRIVATE KEY-----"}'
    r = client.post("/api/credentials/gcp", headers=auth("admin"), json={
        "tenant_id": tenant_id, "gcp_project_id": "proj-1", "bigquery_dataset": "billing_export",
        "service_account_json": sa_json,
    })
    assert r.status_code == 200, r.text

    row = db.query(GcpCostIngestConfig).filter(GcpCostIngestConfig.tenant_id == tenant_id).one()
    stored = row.config.get("encrypted_sa_json", "")
    assert stored and stored != sa_json
    assert "BEGIN PRIVATE KEY" not in str(row.config)
    assert decrypt_secret(stored) == sa_json


def test_azure_credential_update_reencrypts_new_secret(client, auth, db, tenant_id):
    client.post("/api/credentials/azure", headers=auth("admin"), json={
        "tenant_id": tenant_id, "azure_tenant_id": "aad-1", "client_id": "c1",
        "client_secret": "first-secret", "subscription_id": "sub-shared",
    })
    client.post("/api/credentials/azure", headers=auth("admin"), json={
        "tenant_id": tenant_id, "azure_tenant_id": "aad-1", "client_id": "c1",
        "client_secret": "second-secret", "subscription_id": "sub-shared",
    })

    rows = db.query(AzureCostIngestConfig).filter(
        AzureCostIngestConfig.tenant_id == tenant_id, AzureCostIngestConfig.subscription_id == "sub-shared"
    ).all()
    assert len(rows) == 1  # upsert, not duplicate
    assert decrypt_secret(rows[0].config["encrypted_secret"]) == "second-secret"


# ── RBAC on credential endpoints ──────────────────────────────────────────────

def test_credentials_write_requires_permission(client, auth, tenant_id):
    r = client.post("/api/credentials/aws", headers=auth("analyst"), json={
        "tenant_id": tenant_id, "s3_bucket": "my-bucket", "aws_role_arn": "arn:aws:iam::123:role/x",
    })
    assert r.status_code == 403


def test_credentials_delete_requires_admin(client, auth, tenant_id):
    created = client.post("/api/credentials/aws", headers=auth("finops_engineer"), json={
        "tenant_id": tenant_id, "s3_bucket": "another-bucket", "aws_role_arn": "arn:aws:iam::123:role/x",
    })
    assert created.status_code == 200
    config_id = created.json()["id"]

    denied = client.delete(f"/api/credentials/{config_id}", headers=auth("finops_engineer"))
    assert denied.status_code == 403

    allowed = client.delete(f"/api/credentials/{config_id}", headers=auth("admin"))
    assert allowed.status_code == 200


def test_credentials_read_allows_analyst(client, auth, tenant_id):
    r = client.get("/api/credentials", headers=auth("analyst"), params={"tenant_id": tenant_id})
    assert r.status_code == 200
