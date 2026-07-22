"""PII masking utilities for API responses (Stage 19 P2 #3).

Sensitive customer fields (phone/email/tax_id/bank_account) are stored
in DB encrypted (EncryptedStr, see app/core/field_encryption.py) but
**also exposed in API responses**. Without masking, any authenticated
user with `customers:read` permission can see full PII.

This module provides pure-mask functions used at the API boundary:
- Phone: keep first 3 + last 4 digits (138****1234)
- Email: keep first char + domain (a***@example.com)
- tax_id / 统一社会信用代码: keep first 3 + last 3 (91440**********06N)
- Bank account: keep last 4 chars only (******1234)

The decision of *who* sees full vs masked lives in
`app.core.pii_policy.can_view_full_pii`.
"""

from __future__ import annotations

from typing import Callable

# Public field set that should be masked by default.
PII_FIELDS: frozenset[str] = frozenset(
    {
        "phone",
        "invoice_phone",
        "email",
        "tax_id",
        "unified_social_credit_code",
        "bank_account",
    }
)


def mask_phone(value: str | None) -> str | None:
    """Mask phone keeping first 3 and last 4 digits. e.g. 13812348888 -> 138****8888."""
    if not value:
        return value
    digits = "".join(ch for ch in value if ch.isdigit())
    if len(digits) < 7:
        # Too short to safely mask by halves — fall back to all stars.
        return "*" * len(value)
    return f"{digits[:3]}****{digits[-4:]}"


def mask_email(value: str | None) -> str | None:
    """Mask email keeping first char + domain. e.g. alice@example.com -> a****@example.com."""
    if not value or "@" not in value:
        return value
    local, _, domain = value.partition("@")
    if not local:
        return value
    if len(local) == 1:
        masked_local = "*"
    else:
        masked_local = f"{local[0]}{'*' * (len(local) - 1)}"
    return f"{masked_local}@{domain}"


def mask_keep_edges(
    value: str | None,
    *,
    head: int = 3,
    tail: int = 3,
    char: str = "*",
) -> str | None:
    """Mask a string keeping `head` chars at start and `tail` at end.

    Used for tax_id / unified_social_credit_code: 91440300MA5DB0PD3G
    -> 914**********D3G.
    """
    if not value:
        return value
    if len(value) <= head + tail:
        return char * len(value)
    return f"{value[:head]}{char * (len(value) - head - tail)}{value[-tail:]}"


def mask_bank_account(value: str | None) -> str | None:
    """Mask bank account keeping last 4 chars. e.g. 6222021234567890 -> **********7890."""
    if not value:
        return value
    if len(value) <= 4:
        return "*" * len(value)
    return "*" * (len(value) - 4) + value[-4:]


# Field → masker dispatch table. Lambda wrappers normalize signatures.
MASKERS: dict[str, Callable[[str | None], str | None]] = {
    "phone": mask_phone,
    "invoice_phone": mask_phone,
    "email": mask_email,
    "tax_id": lambda v: mask_keep_edges(v, head=3, tail=3),
    "unified_social_credit_code": lambda v: mask_keep_edges(v, head=3, tail=3),
    "bank_account": mask_bank_account,
}


def mask_pii_dict(
    data: dict,
    *,
    fields: frozenset[str] | None = None,
) -> dict:
    """Return a shallow copy of `data` with PII fields masked.

    Non-PII fields pass through untouched. None values are left as None.
    Only string values are masked; non-string PII (int/float/bool) is left
    alone (defense-in-depth: callers should validate upstream).
    """
    fields = fields or PII_FIELDS
    result = dict(data)
    for field in fields:
        if field in result and isinstance(result[field], str):
            masker = MASKERS.get(field, lambda v: mask_keep_edges(v))
            result[field] = masker(result[field])
    return result
