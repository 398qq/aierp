"""Role-based PII visibility policy (Stage 19 P2 #3).

Decision matrix:

| Viewer role             | Record owner == viewer | Sees full PII? |
|-------------------------|------------------------|----------------|
| admin / finance         | any                    | ✅             |
| sales / viewer / other  | yes                    | ✅             |
| sales / viewer / other  | no                     | ❌ (masked)    |

The `owner` field on Customer is the sales rep username
(`Customer.owner`, see backend/app/models/customer.py).
`current_user` is the dict returned by `get_current_user()` in
`app/api/deps.py` with shape: {"user_id", "username", "roles"}.
"""

from __future__ import annotations

from app.utils.pii_masking import mask_pii_dict

# Roles that ALWAYS see full PII regardless of ownership.
FULL_ACCESS_ROLES: frozenset[str] = frozenset({"admin", "finance"})


def can_view_full_pii(
    viewer: dict | None,
    *,
    record_owner: str | None = None,
) -> bool:
    """Return True if `viewer` is allowed to see full PII for the record.

    Args:
        viewer: Current user dict (from get_current_user). None = anonymous.
        record_owner: Customer.owner field value (sales rep username).
            None/empty means unassigned.

    Returns:
        True if the viewer may see full phone/email/tax_id/bank_account;
        False if the response must be masked.
    """
    if not viewer:
        return False

    viewer_roles = set(viewer.get("roles") or ())
    if viewer_roles & FULL_ACCESS_ROLES:
        return True

    username = viewer.get("username")
    if record_owner and username and record_owner == username:
        return True

    return False


def apply_pii_mask(data: dict, viewer: dict | None) -> dict:
    """Per-record PII masking for API response dicts.

    Decision flow:
      1. ``viewer`` is admin/finance -> return as-is (full PII)
      2. ``record_owner`` (``data['owner']``) matches ``viewer.username`` -> full
      3. Otherwise -> mask phone/email/tax_id/unified_social_credit_code/bank_account/invoice_phone

    Returns a shallow copy of ``data`` with masked fields when needed;
    the original dict is returned unchanged when no masking is required.
    Non-dict inputs are passed through (defense-in-depth).
    """
    if not isinstance(data, dict):
        return data
    record_owner = data.get("owner")
    if can_view_full_pii(viewer, record_owner=record_owner):
        return data
    return mask_pii_dict(data)
