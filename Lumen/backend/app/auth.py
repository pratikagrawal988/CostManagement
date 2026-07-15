"""
JWT authentication helpers for Lumen FinOps OS.

Flow:
  POST /api/auth/login   → returns access_token (15 min) + refresh_token (7 days)
  Authorization: Bearer <access_token>  on all protected routes
  GET  /api/auth/me      → returns current user profile

All tokens carry { sub: user_id, tenant_id, role, email }.
"""

from __future__ import annotations

import hashlib
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from passlib.context import CryptContext

try:
    from jose import JWTError, jwt
except ImportError:                        # graceful degradation during tests
    jwt = None                             # type: ignore[assignment]
    JWTError = Exception                   # type: ignore[assignment,misc]

# ── Config ────────────────────────────────────────────────────────────────────

SECRET_KEY   = os.getenv("SECRET_KEY",   "change-me-in-production")
ALGORITHM    = "HS256"
ACCESS_TTL   = int(os.getenv("ACCESS_TOKEN_TTL_MINUTES",  "15"))
REFRESH_TTL  = int(os.getenv("REFRESH_TOKEN_TTL_DAYS",    "7"))

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer  = HTTPBearer(auto_error=False)


# ── Password helpers ──────────────────────────────────────────────────────────

def hash_password(plain: str) -> str:
    return pwd_ctx.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_ctx.verify(plain, hashed)


# ── Token helpers ─────────────────────────────────────────────────────────────

def _now() -> datetime:
    return datetime.now(timezone.utc)


def create_access_token(user_id: str, tenant_id: str, email: str, role: str) -> str:
    expire  = _now() + timedelta(minutes=ACCESS_TTL)
    payload = {
        "sub":       user_id,
        "tenant_id": tenant_id,
        "email":     email,
        "role":      role,
        "exp":       expire,
        "iat":       _now(),
        "type":      "access",
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token() -> tuple[str, str]:
    """Returns (raw_token, sha256_hash) — only the hash is stored in DB."""
    raw   = str(uuid.uuid4())
    h     = hashlib.sha256(raw.encode()).hexdigest()
    return raw, h


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired token: {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


# ── FastAPI dependency ────────────────────────────────────────────────────────

class TokenPayload:
    def __init__(self, data: dict[str, Any]):
        self.user_id:   str = data["sub"]
        self.tenant_id: str = data["tenant_id"]
        self.email:     str = data.get("email", "")
        self.role:      str = data.get("role",  "viewer")

    def require_role(self, *roles: str):
        if self.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{self.role}' is not permitted; required: {roles}",
            )


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> TokenPayload:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No Bearer token provided",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_access_token(credentials.credentials)
    return TokenPayload(payload)


def get_current_tenant(
    current: TokenPayload = Depends(get_current_user),
) -> str:
    """Convenience dependency: just returns the tenant_id string."""
    return current.tenant_id


# ── Optional / dev-mode auth ──────────────────────────────────────────────────
# When DEV_BYPASS_AUTH=true, all requests are treated as tenant-demo / admin.

_DEV_BYPASS = os.getenv("DEV_BYPASS_AUTH", "false").lower() == "true"

_DEV_TOKEN = TokenPayload({
    "sub":       "user-dev",
    "tenant_id": "tenant-demo",
    "email":     "dev@lumen.local",
    "role":      "admin",
})


def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> TokenPayload:
    """Like get_current_user but falls back to dev token when bypass is enabled.

    A real Bearer token, when presented, is always honored — even in dev mode —
    so RBAC enforcement can be exercised. The dev-admin fallback applies only
    to unauthenticated requests.
    """
    if credentials is not None:
        return get_current_user(credentials)
    if _DEV_BYPASS:
        return _DEV_TOKEN
    return get_current_user(credentials)


def get_optional_tenant(
    current: TokenPayload = Depends(get_optional_user),
) -> str:
    return current.tenant_id
