"""
Auth routes — login, register, refresh, me, logout.

POST /api/auth/register    — create user + tenant (self-serve signup)
POST /api/auth/login       — returns access + refresh tokens
POST /api/auth/refresh     — rotate refresh token
GET  /api/auth/me          — current user profile
POST /api/auth/logout      — revoke refresh token
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from .auth import (
    create_access_token,
    create_refresh_token,
    get_current_user,
    hash_password,
    TokenPayload,
    verify_password,
    REFRESH_TTL,
)
from .database import get_db
from .models import Tenant, utcnow, new_id

router = APIRouter(prefix="/api/auth", tags=["auth"])


# ── Pydantic schemas ──────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email:       str
    password:    str
    full_name:   str = ""
    tenant_name: str = ""          # if blank, derived from email domain


class LoginRequest(BaseModel):
    email:    str
    password: str


class TokenResponse(BaseModel):
    access_token:  str
    refresh_token: str
    token_type:    str = "bearer"
    user_id:       str
    tenant_id:     str
    email:         str
    role:          str


class RefreshRequest(BaseModel):
    refresh_token: str


# ── Helpers ───────────────────────────────────────────────────────────────────

def _hash_rt(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def _get_user_model():
    """Lazy import to avoid circular at module load time."""
    from .models import User
    return User


def _get_rt_model():
    from .models import RefreshToken
    return RefreshToken


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/register", response_model=TokenResponse, status_code=201)
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    User         = _get_user_model()
    RefreshToken = _get_rt_model()

    # Derive tenant name
    tenant_name = req.tenant_name or req.email.split("@")[-1]

    # Create tenant (or reuse if demo tenant email)
    tenant_id = f"tenant-{uuid.uuid4().hex[:8]}"
    existing_tenant = db.query(Tenant).filter_by(id="tenant-demo").first()

    if req.email.endswith("@lumen.local") or req.email.endswith("@demo.local"):
        # Wire into the demo tenant for easy testing
        tenant = existing_tenant or db.query(Tenant).first()
        if not tenant:
            tenant = Tenant(id="tenant-demo", name="Demo Tenant", status="active")
            db.add(tenant)
            db.flush()
        tenant_id = tenant.id
    else:
        tenant = Tenant(id=tenant_id, name=tenant_name, status="active")
        db.add(tenant)
        db.flush()

    # Check duplicate email within tenant
    existing = db.query(User).filter_by(tenant_id=tenant_id, email=req.email).first()
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered in this tenant")

    user = User(
        id              = new_id(),
        tenant_id       = tenant_id,
        email           = req.email,
        hashed_password = hash_password(req.password),
        full_name       = req.full_name,
        role            = "admin",   # first user in tenant = admin
        is_active       = True,
    )
    db.add(user)
    db.flush()

    # Issue tokens
    access_token      = create_access_token(user.id, tenant_id, user.email, user.role)
    raw_rt, rt_hash   = create_refresh_token()
    expires           = datetime.now(timezone.utc) + timedelta(days=REFRESH_TTL)

    rt = RefreshToken(
        id         = new_id(),
        user_id    = user.id,
        tenant_id  = tenant_id,
        token_hash = rt_hash,
        expires_at = expires,
    )
    db.add(rt)
    db.commit()

    return TokenResponse(
        access_token  = access_token,
        refresh_token = raw_rt,
        user_id       = user.id,
        tenant_id     = tenant_id,
        email         = user.email,
        role          = user.role,
    )


@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    User         = _get_user_model()
    RefreshToken = _get_rt_model()

    user = db.query(User).filter_by(email=req.email).first()
    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account disabled")

    # Update last_login_at
    user.last_login_at = utcnow()
    db.flush()

    access_token    = create_access_token(user.id, user.tenant_id, user.email, user.role)
    raw_rt, rt_hash = create_refresh_token()
    expires         = datetime.now(timezone.utc) + timedelta(days=REFRESH_TTL)

    rt = RefreshToken(
        id         = new_id(),
        user_id    = user.id,
        tenant_id  = user.tenant_id,
        token_hash = rt_hash,
        expires_at = expires,
    )
    db.add(rt)
    db.commit()

    return TokenResponse(
        access_token  = access_token,
        refresh_token = raw_rt,
        user_id       = user.id,
        tenant_id     = user.tenant_id,
        email         = user.email,
        role          = user.role,
    )


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(req: RefreshRequest, db: Session = Depends(get_db)):
    User         = _get_user_model()
    RefreshToken = _get_rt_model()

    rt_hash = _hash_rt(req.refresh_token)
    rt      = db.query(RefreshToken).filter_by(token_hash=rt_hash).first()

    if not rt or rt.revoked:
        raise HTTPException(status_code=401, detail="Invalid or revoked refresh token")
    if rt.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Refresh token expired")

    user = db.query(User).filter_by(id=rt.user_id).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or disabled")

    # Rotate: revoke old, issue new
    rt.revoked = True
    db.flush()

    access_token    = create_access_token(user.id, user.tenant_id, user.email, user.role)
    raw_new, new_hash = create_refresh_token()
    expires         = datetime.now(timezone.utc) + timedelta(days=REFRESH_TTL)

    new_rt = RefreshToken(
        id         = new_id(),
        user_id    = user.id,
        tenant_id  = user.tenant_id,
        token_hash = new_hash,
        expires_at = expires,
    )
    db.add(new_rt)
    db.commit()

    return TokenResponse(
        access_token  = access_token,
        refresh_token = raw_new,
        user_id       = user.id,
        tenant_id     = user.tenant_id,
        email         = user.email,
        role          = user.role,
    )


@router.get("/me")
def me(current: TokenPayload = Depends(get_current_user), db: Session = Depends(get_db)):
    User = _get_user_model()
    user = db.query(User).filter_by(id=current.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "user_id":   user.id,
        "tenant_id": user.tenant_id,
        "email":     user.email,
        "full_name": user.full_name,
        "role":      user.role,
    }


@router.post("/logout", status_code=204)
def logout(req: RefreshRequest, db: Session = Depends(get_db)):
    RefreshToken = _get_rt_model()
    rt_hash = _hash_rt(req.refresh_token)
    rt      = db.query(RefreshToken).filter_by(token_hash=rt_hash).first()
    if rt:
        rt.revoked = True
        db.commit()
