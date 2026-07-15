"""
User management & audit endpoints (admin only).

- GET    /api/users              → list tenant users
- POST   /api/users              → create user (with role)
- PATCH  /api/users/{user_id}    → change role / name / active flag
- DELETE /api/users/{user_id}    → deactivate (soft delete)
- GET    /api/users/roles        → role catalog with descriptions
- GET    /api/audit              → recent audit events
"""

from __future__ import annotations

from typing import Optional

import re

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

from .auth import TokenPayload, hash_password
from .database import get_db
from .models import AuditEvent, User, utcnow
from .rbac import ROLES, normalize_role, record_audit, require_permission

router = APIRouter(prefix="/api/users", tags=["users"])
audit_router = APIRouter(prefix="/api/audit", tags=["audit"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class CreateUserRequest(BaseModel):
    email: str
    full_name: str = ""
    role: str = "viewer"
    password: str


class UpdateUserRequest(BaseModel):
    full_name: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None


def _fmt(u: User) -> dict:
    return {
        "id": u.id,
        "email": u.email,
        "full_name": u.full_name,
        "role": normalize_role(u.role),
        "is_active": u.is_active,
        "last_login_at": u.last_login_at.isoformat() if u.last_login_at else None,
        "created_at": u.created_at.isoformat(),
    }


# ── Role catalog ──────────────────────────────────────────────────────────────

@router.get("/roles")
def list_roles(current: TokenPayload = Depends(require_permission("users:read"))):
    return {"roles": [{"id": k, "description": v} for k, v in ROLES.items()]}


# ── User CRUD ─────────────────────────────────────────────────────────────────

@router.get("")
def list_users(
    current: TokenPayload = Depends(require_permission("users:read")),
    db: Session = Depends(get_db),
):
    users = (
        db.query(User)
        .filter(User.tenant_id == current.tenant_id)
        .order_by(User.created_at)
        .all()
    )
    return {"count": len(users), "users": [_fmt(u) for u in users]}


@router.post("", status_code=201)
def create_user(
    req: CreateUserRequest,
    current: TokenPayload = Depends(require_permission("users:manage")),
    db: Session = Depends(get_db),
):
    role = normalize_role(req.role)
    if role not in ROLES:
        raise HTTPException(400, f"Unknown role '{req.role}'. Valid: {sorted(ROLES)}")
    if not _EMAIL_RE.match(req.email):
        raise HTTPException(400, "Invalid email address")
    if len(req.password) < 8:
        raise HTTPException(400, "Password must be at least 8 characters")

    exists = db.query(User).filter(
        User.tenant_id == current.tenant_id, User.email == req.email.lower()
    ).one_or_none()
    if exists:
        raise HTTPException(409, "A user with this email already exists")

    user = User(
        tenant_id=current.tenant_id,
        email=req.email.lower(),
        full_name=req.full_name,
        role=role,
        hashed_password=hash_password(req.password),
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    record_audit(db, current, action="user.create", resource_type="user",
                 resource_id=user.id, detail={"email": user.email, "assigned_role": role})
    return _fmt(user)


@router.patch("/{user_id}")
def update_user(
    user_id: str,
    req: UpdateUserRequest,
    current: TokenPayload = Depends(require_permission("users:manage")),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(
        User.id == user_id, User.tenant_id == current.tenant_id
    ).one_or_none()
    if not user:
        raise HTTPException(404, "User not found")

    changes = {}
    if req.role is not None:
        role = normalize_role(req.role)
        if role not in ROLES:
            raise HTTPException(400, f"Unknown role '{req.role}'. Valid: {sorted(ROLES)}")
        if user.id == current.user_id and role != "admin":
            raise HTTPException(400, "You cannot remove your own admin role")
        changes["role"] = {"from": normalize_role(user.role), "to": role}
        user.role = role
    if req.full_name is not None:
        changes["full_name"] = {"from": user.full_name, "to": req.full_name}
        user.full_name = req.full_name
    if req.is_active is not None:
        if user.id == current.user_id and not req.is_active:
            raise HTTPException(400, "You cannot deactivate your own account")
        changes["is_active"] = {"from": user.is_active, "to": req.is_active}
        user.is_active = req.is_active

    user.updated_at = utcnow()
    db.commit()
    db.refresh(user)

    record_audit(db, current, action="user.update", resource_type="user",
                 resource_id=user.id, detail={"email": user.email, "changes": changes})
    return _fmt(user)


@router.delete("/{user_id}")
def deactivate_user(
    user_id: str,
    current: TokenPayload = Depends(require_permission("users:manage")),
    db: Session = Depends(get_db),
):
    if user_id == current.user_id:
        raise HTTPException(400, "You cannot deactivate your own account")
    user = db.query(User).filter(
        User.id == user_id, User.tenant_id == current.tenant_id
    ).one_or_none()
    if not user:
        raise HTTPException(404, "User not found")

    user.is_active = False
    user.updated_at = utcnow()
    db.commit()

    record_audit(db, current, action="user.deactivate", resource_type="user",
                 resource_id=user.id, detail={"email": user.email})
    return {"status": "deactivated", "id": user.id}


# ── Audit log ─────────────────────────────────────────────────────────────────

@audit_router.get("")
def list_audit_events(
    current: TokenPayload = Depends(require_permission("audit:read")),
    limit: int = Query(50, le=500),
    action: Optional[str] = Query(None, description="Filter by event_type prefix, e.g. 'user.' or 'credential.'"),
    db: Session = Depends(get_db),
):
    q = db.query(AuditEvent).filter(AuditEvent.tenant_id == current.tenant_id)
    if action:
        q = q.filter(AuditEvent.event_type.like(f"{action}%"))
    events = q.order_by(AuditEvent.created_at.desc()).limit(limit).all()
    return {
        "count": len(events),
        "events": [
            {
                "id": e.id,
                "actor": e.actor,
                "action": e.event_type,
                "resource_type": e.entity_type,
                "resource_id": e.entity_id,
                "payload": e.payload,
                "created_at": e.created_at.isoformat(),
            }
            for e in events
        ],
    }
