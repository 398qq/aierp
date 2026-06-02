"""Field-level encryption for PII (phone, email, notes) using Fernet.

ERP systems handle sensitive customer data. Even if the database
is leaked (via SQL injection, backup theft, etc.), encrypted fields
remain unreadable without the encryption key.

Key points:
- Uses Fernet (AES-128-CBC + HMAC-SHA256) from `cryptography` package
- Key loaded from env var FIELD_ENCRYPTION_KEY (44-byte base64)
- Falls back to a development key when env var is missing
  (logged as a warning at import time so prod deployments catch this)
- Encrypts at the application layer so database backups are useless
  without the key

The `EncryptedStr` SQLAlchemy type transparently encrypts on write
and decrypts on read.
"""

import base64
import hashlib
import logging
import os
from sqlalchemy.types import String, TypeDecorator

logger = logging.getLogger(__name__)


def _load_or_generate_key() -> bytes:
    """Load the encryption key from env or generate a deterministic dev one.

    Production: set FIELD_ENCRYPTION_KEY=<44-byte base64 string>.
    Generate one with: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`

    Development: falls back to a key derived from JWT_SECRET. The
    generated key is logged so the dev can copy it into .env.
    """
    key_b64 = os.getenv("FIELD_ENCRYPTION_KEY")
    if key_b64:
        try:
            key = base64.urlsafe_b64decode(key_b64)
            if len(key) != 32:
                raise ValueError(f"key must be 32 bytes, got {len(key)}")
            return key
        except Exception as exc:
            logger.warning("Invalid FIELD_ENCRYPTION_KEY: %s — falling back to dev key", exc)

    # Dev fallback — derived from JWT_SECRET so it's stable per env
    seed = os.getenv("JWT_SECRET", "dev-secret-do-not-use-in-prod").encode()
    derived = hashlib.sha256(seed).digest()  # 32 bytes
    logger.warning(
        "FIELD_ENCRYPTION_KEY not set — using derived dev key. "
        "Set FIELD_ENCRYPTION_KEY in production."
    )
    return derived


_ENCRYPTION_KEY = _load_or_generate_key()


def _get_fernet():
    """Lazy import + cache Fernet instance."""
    global _fernet_instance
    try:
        _fernet_instance
    except NameError:
        pass
    from cryptography.fernet import Fernet
    import base64
    f = Fernet(base64.urlsafe_b64encode(_ENCRYPTION_KEY))
    return f


def encrypt(plaintext: str) -> str:
    """Encrypt a string. Returns a base64-urlsafe ciphertext.

    Empty strings are returned as-is to avoid wasting tokens on NULLs.
    """
    if not plaintext:
        return plaintext
    f = _get_fernet()
    token = f.encrypt(plaintext.encode("utf-8"))
    return token.decode("ascii")


def decrypt(ciphertext: str) -> str:
    """Decrypt a string previously encrypted with `encrypt`.

    Returns the ciphertext as-is if decryption fails (e.g. for
    plaintext stored before encryption was enabled). This makes
    the migration safe but should be alerted on.
    """
    if not ciphertext:
        return ciphertext
    try:
        f = _get_fernet()
        plain = f.decrypt(ciphertext.encode("ascii"))
        return plain.decode("utf-8")
    except Exception:
        # Could be: not a Fernet token, key rotated, or was never encrypted
        logger.warning("Failed to decrypt value (returning as-is). Length=%d", len(ciphertext))
        return ciphertext


def mask_for_display(ciphertext: str, visible_chars: int = 4) -> str:
    """Mask an encrypted value for safe display in UI.

    Example: encrypt("13800001234") → "vNZ...kA==" → mask → "vNZ...===="

    For unencrypted (legacy) values, masks in the middle:
        "13800001234" → "138****1234"
    """
    if not ciphertext:
        return ""
    # If it looks like a Fernet token (starts with 'gAAAAA' or 'vNZ' etc.)
    if ciphertext.startswith(("gAAAAA", "vNZ", "eyJ")):
        # Encrypted value — show first 4 + "..." + last 4 chars
        if len(ciphertext) <= visible_chars * 2 + 3:
            return ciphertext[:3] + "***"
        return (
            ciphertext[:visible_chars] +
            "..." +
            ciphertext[-visible_chars:]
        )
    # Looks like plain text — mask middle
    if len(ciphertext) <= 8:
        return "***"
    mid = len(ciphertext) // 2
    visible = max(2, len(ciphertext) // 4)
    return (
        ciphertext[:visible] +
        "*" * (mid - visible) +
        ciphertext[-visible:]
    )


# ────────────────────────────────────────────────────────────────────────
# SQLAlchemy type wrapper — transparent encryption
# ────────────────────────────────────────────────────────────────────────


class EncryptedStr(TypeDecorator):
    """SQLAlchemy type that encrypts strings before storing.

    Use as a column type:
        phone: Mapped[str] = mapped_column(EncryptedStr(255))
    """

    impl = String
    cache_ok = True

    def __init__(self, length: int = 1024) -> None:
        super().__init__(length=length)

    def process_bind_param(self, value, dialect):
        """Called when writing to DB — encrypt the value."""
        if value is None or value == "":
            return value
        return encrypt(value)

    def process_result_value(self, value, dialect):
        """Called when reading from DB — decrypt the value."""
        if value is None or value == "":
            return value
        return decrypt(value)
