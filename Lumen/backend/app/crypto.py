"""
Secret encryption for credential material at rest.

Envelope-style, versioned format so the backing key mechanism can be swapped
(env key today → KMS/Vault later) without a data migration:

    v1:<fernet-token>     Fernet (AES-128-CBC + HMAC-SHA256), key from env
    <anything else>       legacy value (plain base64 from the pre-encryption era)

Key management:
    SECRET_ENCRYPTION_KEY   urlsafe-base64 32-byte key. Generate with:
        python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

    If unset, a key is derived from the JWT signing secret so dev environments
    keep working — a startup warning is logged. Set a dedicated key in any
    real deployment, and move to KMS/Vault before production.

Never log plaintext or ciphertext values.
"""

from __future__ import annotations

import base64
import hashlib
import logging
import os

from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)

_PREFIX = "v1:"


def _load_key() -> bytes:
    key = os.getenv("SECRET_ENCRYPTION_KEY", "").strip()
    if key:
        return key.encode()
    # Dev fallback: derive from JWT secret so the stack works out of the box.
    jwt_secret = os.getenv("JWT_SECRET", "lumen-dev-secret")
    logger.warning(
        "SECRET_ENCRYPTION_KEY not set — deriving encryption key from JWT secret. "
        "Set a dedicated key (and plan KMS/Vault) for production."
    )
    digest = hashlib.sha256(f"lumen-secret-encryption:{jwt_secret}".encode()).digest()
    return base64.urlsafe_b64encode(digest)


_fernet = Fernet(_load_key())


def encrypt_secret(plaintext: str) -> str:
    """Encrypt a secret for storage. Returns versioned ciphertext."""
    if not plaintext:
        return ""
    return _PREFIX + _fernet.encrypt(plaintext.encode()).decode()


def decrypt_secret(stored: str) -> str:
    """Decrypt a stored secret.

    Handles the legacy plain-base64 format transparently so existing rows
    keep working; they are upgraded to v1 on next write.
    """
    if not stored:
        return ""
    if stored.startswith(_PREFIX):
        try:
            return _fernet.decrypt(stored[len(_PREFIX):].encode()).decode()
        except InvalidToken:
            raise ValueError(
                "Could not decrypt secret — SECRET_ENCRYPTION_KEY differs from the "
                "key used at encryption time."
            )
    # Legacy: pre-encryption rows stored plain base64
    try:
        return base64.b64decode(stored.encode()).decode()
    except Exception:
        raise ValueError("Stored secret is in an unrecognized format.")


def is_encrypted(stored: str) -> bool:
    return bool(stored) and stored.startswith(_PREFIX)
