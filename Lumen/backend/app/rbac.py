"""
RBAC — role catalog, permission checks, and audit logging.

Role hierarchy (per RBAC_AND_AI_DASHBOARD_SPECS.md):
    admin > finops_engineer / finance_manager / team_lead > analyst > viewer

Usage:
    @router.post("/thing", dependencies=[Depends(require_permission("credentials:write"))])
    ...
    record_audit(db, user, action="credential.create", resource_type="azure_config",
                 resource_id=cfg.id, detail={"subscription": "..."})
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import Depends, HTTPException, status

from .auth import TokenPayload, get_optional_user

# ── Role catalog ──────────────────────────────────────────────────────────────

ROLES: dict[str, str] = {
    "admin":           "FinOps Admin — full access incl. user management and system settings",
    "finops_engineer": "FinOps Engineer — configs (create/test, no delete), all dashboards, recommendations",
    "finance_manager": "Finance Manager — read-only configs, budgets and alerts, finance dashboards",
    "team_lead":       "Team Lead — assigned team costs and budgets only",
    "analyst":         "Finance Analyst — all dashboards read-only, reports and exports",
    "viewer":          "Viewer — Executive Summary and high-level metrics only",
}

# Legacy role names still present in older user rows map onto the catalog.
_ROLE_ALIASES = {"engineer": "finops_engineer", "manager": "finance_manager"}


def normalize_role(role: str) -> str:
    role = (role or "viewer").strip().lower()
    return _ROLE_ALIASES.get(role, role)


# ── Permission matrix ─────────────────────────────────────────────────────────
# Keep permissions coarse and additive; a role has a permission iff listed.

PERMISSIONS: dict[str, set[str]] = {
    # Cloud credential configs
    "credentials:read":   {"admin", "finops_engineer", "finance_manager", "analyst"},
    "credentials:write":  {"admin", "finops_engineer"},          # create / update / test
    "credentials:delete": {"admin"},
    # Budgets & alerts
    "budgets:read":       {"admin", "finops_engineer", "finance_manager", "team_lead", "analyst"},
    "budgets:write":      {"admin", "finance_manager"},
    # Users, roles, audit
    "users:read":         {"admin"},
    "users:manage":       {"admin"},
    "audit:read":         {"admin"},
    # Recommendations
    "recommendations:read":  {"admin", "finops_engineer", "analyst"},
    "recommendations:write": {"admin", "finops_engineer"},
}


def has_permission(role: str, permission: str) -> bool:
    return normalize_role(role) in PERMISSIONS.get(permission, set())


def require_permission(permission: str):
    """FastAPI dependency factory: 403 unless the current user's role grants it."""

    def _checker(current: TokenPayload = Depends(get_optional_user)) -> TokenPayload:
        if not has_permission(current.role, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{current.role}' lacks permission '{permission}'",
            )
        return current

    return _checker


# ── Audit logging ─────────────────────────────────────────────────────────────

def record_audit(
    db,
    user: Optional[TokenPayload],
    action: str,
    resource_type: str = "",
    resource_id: str = "",
    detail: Optional[dict[str, Any]] = None,
    status_str: str = "success",
) -> None:
    """Write one audit row (reuses the AuditEvent table). Never raises —
    auditing must not break the request."""
    try:
        from .models import AuditEvent  # local import to avoid cycles

        db.add(AuditEvent(
            tenant_id=user.tenant_id if user else "tenant-demo",
            actor=(user.email or user.user_id) if user else "anonymous",
            entity_type=resource_type or "system",
            entity_id=resource_id or "-",
            event_type=action,
            payload={
                "status": status_str,
                "user_id": user.user_id if user else None,
                "role": user.role if user else None,
                **_scrub(detail or {}),
            },
        ))
        db.commit()
    except Exception:  # pragma: no cover
        import logging
        logging.getLogger(__name__).exception("Failed to write audit log for %s", action)
        try:
            db.rollback()
        except Exception:
            pass


_SENSITIVE_KEYS = {"client_secret", "service_account_json", "service_account_key",
                   "password", "hashed_password", "token", "secret", "aws_external_id"}


def _scrub(detail: dict[str, Any]) -> dict[str, Any]:
    """Never persist secret material in audit rows."""
    return {k: ("***" if k.lower() in _SENSITIVE_KEYS else v) for k, v in detail.items()}
