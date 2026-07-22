"""Tests for PII masking utilities and policy (Stage 19 P2 #3).

Covers:
- Pure mask functions: phone / email / tax_id / bank_account / keep-edges
- ``mask_pii_dict``: shallow copy with selected fields masked
- ``can_view_full_pii``: admin / finance / owner / other roles
- ``apply_pii_mask``: end-to-end per-record decision + masking
"""

from __future__ import annotations

import pytest

from app.core.pii_policy import (
    FULL_ACCESS_ROLES,
    apply_pii_mask,
    can_view_full_pii,
)
from app.utils.pii_masking import (
    MASKERS,
    PII_FIELDS,
    mask_bank_account,
    mask_email,
    mask_keep_edges,
    mask_phone,
    mask_pii_dict,
)


# ---------------------------------------------------------------------------
# Pure maskers
# ---------------------------------------------------------------------------


class TestMaskPhone:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("13812348888", "138****8888"),
            ("+86 138-1234-8888", "861****8888"),  # 14 digits after strip
            ("1381234567", "138****4567"),  # 10 digits, normal path
            ("123456", "******"),  # 6 digits < 7 -> fully starred
            ("", ""),  # empty passthrough
            (None, None),
        ],
    )
    def test_masks_expected(self, raw, expected):
        assert mask_phone(raw) == expected


class TestMaskEmail:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("alice@example.com", "a****@example.com"),
            ("a@example.com", "*@example.com"),
            ("bob.smith@corp.io", "b********@corp.io"),
            ("noatsign", "noatsign"),
            ("", ""),  # empty passthrough (no @)
            (None, None),
        ],
    )
    def test_masks_expected(self, raw, expected):
        assert mask_email(raw) == expected


class TestMaskKeepEdges:
    def test_typical(self):
        # 18 chars - 3 - 3 = 12 stars in middle
        assert mask_keep_edges("91440300MA5DB0PD3G") == "914************D3G"

    def test_short_string_fully_masked(self):
        assert mask_keep_edges("abc", head=3, tail=3) == "***"

    def test_empty(self):
        assert mask_keep_edges("") == ""
        assert mask_keep_edges(None) is None


class TestMaskBankAccount:
    def test_typical(self):
        # 16 chars - 4 = 12 stars prefix
        assert mask_bank_account("6222021234567890") == "************7890"

    def test_short_falls_back(self):
        assert mask_bank_account("1234") == "****"
        assert mask_bank_account("12") == "**"

    def test_empty(self):
        assert mask_bank_account("") == ""
        assert mask_bank_account(None) is None


# ---------------------------------------------------------------------------
# mask_pii_dict
# ---------------------------------------------------------------------------


def test_mask_pii_dict_only_masks_listed_fields():
    data = {
        "name": "Acme Corp",
        "phone": "13812348888",
        "email": "alice@example.com",
        "owner": "robin",
        "level": "A",
    }
    masked = mask_pii_dict(data)
    # Non-PII untouched
    assert masked["name"] == "Acme Corp"
    assert masked["owner"] == "robin"
    assert masked["level"] == "A"
    # PII masked
    assert masked["phone"] == "138****8888"
    assert masked["email"] == "a****@example.com"


def test_mask_pii_dict_returns_shallow_copy():
    data = {"phone": "13812348888"}
    masked = mask_pii_dict(data)
    assert masked is not data
    assert data["phone"] == "13812348888"  # original untouched


def test_mask_pii_dict_skips_non_string_pii():
    # Defensive: integers, None, etc. should be left alone
    data = {"phone": None, "bank_account": 12345, "tax_id": ""}
    masked = mask_pii_dict(data)
    assert masked == data


def test_mask_pii_dict_custom_fields():
    data = {"phone": "13812348888", "tax_id": "91440300MA5DB0PD3G"}
    masked = mask_pii_dict(data, fields=frozenset({"phone"}))
    assert masked["phone"] == "138****8888"
    assert masked["tax_id"] == "91440300MA5DB0PD3G"  # not in custom fields


def test_all_pii_fields_have_maskers():
    """PII_FIELDS must be a subset of MASKERS keys — defensive."""
    missing = PII_FIELDS - set(MASKERS.keys())
    assert not missing, f"Missing maskers for PII fields: {missing}"


# ---------------------------------------------------------------------------
# can_view_full_pii — policy
# ---------------------------------------------------------------------------


ADMIN = {"user_id": 1, "username": "admin1", "roles": ["admin"]}
FINANCE = {"user_id": 2, "username": "fin1", "roles": ["finance"]}
SALES_OWNER = {"user_id": 3, "username": "robin", "roles": ["sales"]}
SALES_OTHER = {"user_id": 4, "username": "alice", "roles": ["sales"]}
VIEWER = {"user_id": 5, "username": "viewer1", "roles": ["viewer"]}
ANON = None


class TestCanViewFullPii:
    def test_admin_sees_full(self):
        assert can_view_full_pii(ADMIN, record_owner="robin") is True

    def test_finance_sees_full(self):
        assert can_view_full_pii(FINANCE, record_owner="alice") is True

    def test_sales_owner_sees_own_full(self):
        assert can_view_full_pii(SALES_OWNER, record_owner="robin") is True

    def test_sales_other_sees_masked(self):
        assert can_view_full_pii(SALES_OTHER, record_owner="robin") is False

    def test_viewer_never_sees_full(self):
        assert can_view_full_pii(VIEWER, record_owner="robin") is False
        assert can_view_full_pii(VIEWER, record_owner="viewer1") is True

    def test_anonymous_sees_nothing(self):
        assert can_view_full_pii(ANON, record_owner="robin") is False

    def test_no_record_owner_means_only_admins(self):
        assert can_view_full_pii(SALES_OWNER, record_owner=None) is False
        assert can_view_full_pii(ADMIN, record_owner=None) is True

    def test_full_access_roles_constant(self):
        assert "admin" in FULL_ACCESS_ROLES
        assert "finance" in FULL_ACCESS_ROLES


# ---------------------------------------------------------------------------
# apply_pii_mask — end-to-end
# ---------------------------------------------------------------------------


def _customer_dict(owner="robin") -> dict:
    return {
        "id": 100,
        "name": "Acme Corp",
        "owner": owner,
        "phone": "13812348888",
        "email": "contact@acme.com",
        "tax_id": "91440300MA5DB0PD3G",
        "bank_account": "6222021234567890",
        "invoice_phone": "021-12345678",
        "level": "A",
    }


def test_apply_pii_mask_admin_returns_unchanged():
    data = _customer_dict()
    out = apply_pii_mask(data, ADMIN)
    assert out is data  # no copy, full PII
    assert out["phone"] == "13812348888"


def test_apply_pii_mask_owner_returns_unchanged():
    data = _customer_dict(owner="robin")
    out = apply_pii_mask(data, SALES_OWNER)
    assert out is data
    assert out["phone"] == "13812348888"


def test_apply_pii_mask_other_role_masks_pii():
    data = _customer_dict(owner="robin")
    out = apply_pii_mask(data, SALES_OTHER)
    assert out["phone"] == "138****8888"
    assert out["email"] == "c******@acme.com"
    assert out["tax_id"] == "914************D3G"  # 12 stars middle
    assert out["bank_account"] == "************7890"  # 12 stars prefix
    assert out["invoice_phone"] == "021****5678"  # 11 digits after stripping
    # Non-PII fields untouched
    assert out["name"] == "Acme Corp"
    assert out["level"] == "A"


def test_apply_pii_mask_viewer_masks_pii():
    data = _customer_dict(owner="robin")
    out = apply_pii_mask(data, VIEWER)
    assert out["phone"] == "138****8888"


def test_apply_pii_mask_non_dict_passes_through():
    assert apply_pii_mask(None, ADMIN) is None
    assert apply_pii_mask("string", ADMIN) == "string"
    assert apply_pii_mask(123, ADMIN) == 123


def test_apply_pii_mask_does_not_mutate_input():
    data = _customer_dict(owner="alice")
    _ = apply_pii_mask(data, VIEWER)
    # Original must still have full PII
    assert data["phone"] == "13812348888"
    assert data["email"] == "contact@acme.com"
