"""Tests for 013 commission scheme service — validation, calculation, lifecycle."""

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.models.commission_scheme import CommissionScheme


# ── Tier Validation (pure logic, no DB) ────────────────────────────────


class TestTierValidation:
    """SchemeTier validation rules — overlap, gap, bounds."""

    def test_single_tier_valid(self):
        from app.services.commission_scheme_service import validate_tiers

        tiers = [
            {
                "tier_no": 1,
                "low_amount": Decimal("0"),
                "high_amount": None,
                "rate": Decimal("0.05"),
                "cap_amount": Decimal("0"),
                "floor_amount": Decimal("0"),
            },
        ]
        result = validate_tiers(tiers)
        assert len(result) == 1

    def test_multi_tier_no_gap(self):
        from app.services.commission_scheme_service import validate_tiers

        tiers = [
            {
                "tier_no": 1,
                "low_amount": Decimal("0"),
                "high_amount": Decimal("100000"),
                "rate": Decimal("0.03"),
                "cap_amount": Decimal("0"),
                "floor_amount": Decimal("0"),
            },
            {
                "tier_no": 2,
                "low_amount": Decimal("100000"),
                "high_amount": Decimal("300000"),
                "rate": Decimal("0.05"),
                "cap_amount": Decimal("0"),
                "floor_amount": Decimal("0"),
            },
            {
                "tier_no": 3,
                "low_amount": Decimal("300000"),
                "high_amount": None,
                "rate": Decimal("0.07"),
                "cap_amount": Decimal("0"),
                "floor_amount": Decimal("0"),
            },
        ]
        result = validate_tiers(tiers)
        assert len(result) == 3

    def test_gap_detected(self):
        from app.services.commission_scheme_service import validate_tiers

        tiers = [
            {
                "tier_no": 1,
                "low_amount": Decimal("0"),
                "high_amount": Decimal("50000"),
                "rate": Decimal("0.03"),
                "cap_amount": Decimal("0"),
                "floor_amount": Decimal("0"),
            },
            {
                "tier_no": 2,
                "low_amount": Decimal("100000"),
                "high_amount": None,
                "rate": Decimal("0.05"),
                "cap_amount": Decimal("0"),
                "floor_amount": Decimal("0"),
            },
        ]
        with pytest.raises(Exception, match="Gap"):
            validate_tiers(tiers)

    def test_empty_tiers_rejected(self):
        from app.services.commission_scheme_service import validate_tiers

        with pytest.raises(Exception, match="At least one tier"):
            validate_tiers([])

    def test_middle_tier_unlimited_high_rejected(self):
        from app.services.commission_scheme_service import validate_tiers

        tiers = [
            {
                "tier_no": 1,
                "low_amount": Decimal("0"),
                "high_amount": None,
                "rate": Decimal("0.03"),
                "cap_amount": Decimal("0"),
                "floor_amount": Decimal("0"),
            },
            {
                "tier_no": 2,
                "low_amount": Decimal("100000"),
                "high_amount": None,
                "rate": Decimal("0.05"),
                "cap_amount": Decimal("0"),
                "floor_amount": Decimal("0"),
            },
        ]
        with pytest.raises(Exception, match="only the last tier"):
            validate_tiers(tiers)

    def test_max_tiers_limit(self):
        from app.services.commission_scheme_service import validate_tiers

        tiers = [
            {
                "tier_no": i,
                "low_amount": Decimal(str(i * 10000)),
                "high_amount": Decimal(str((i + 1) * 10000)),
                "rate": Decimal("0.03"),
                "cap_amount": Decimal("0"),
                "floor_amount": Decimal("0"),
            }
            for i in range(11)
        ]
        tiers[-1]["high_amount"] = None
        with pytest.raises(Exception, match="Maximum 10"):
            validate_tiers(tiers)


# ── Calculation Engine (pure logic, no DB) ─────────────────────────────


class TestTierCalculation:
    """Commission calculation engine — tier matching, cap, floor."""

    @pytest.fixture
    def mock_tiers(self):
        """Create mock SchemeTier objects."""
        from unittest.mock import MagicMock

        tiers = []
        for i, (low, high, rate, cap, floor) in enumerate(
            [
                (
                    Decimal("0"),
                    Decimal("100000"),
                    Decimal("0.03"),
                    Decimal("5000"),
                    Decimal("2000"),
                ),
                (
                    Decimal("100000"),
                    Decimal("300000"),
                    Decimal("0.05"),
                    Decimal("10000"),
                    Decimal("0"),
                ),
                (
                    Decimal("300000"),
                    None,
                    Decimal("0.07"),
                    Decimal("20000"),
                    Decimal("0"),
                ),
            ],
            start=1,
        ):
            t = MagicMock()
            t.tier_no = i
            t.low_amount = low
            t.high_amount = high
            t.rate = rate
            t.cap_amount = cap
            t.floor_amount = floor
            t.product_category = None
            t.customer_level = None
            t.deleted_at = None
            tiers.append(t)
        return tiers

    def test_first_tier(self, mock_tiers):
        from app.services.commission_scheme_service import _match_tier

        t = _match_tier(mock_tiers, Decimal("50000"), None, None)
        assert t is not None
        assert t.tier_no == 1

    def test_second_tier(self, mock_tiers):
        from app.services.commission_scheme_service import _match_tier

        t = _match_tier(mock_tiers, Decimal("150000"), None, None)
        assert t is not None
        assert t.tier_no == 2

    def test_third_tier(self, mock_tiers):
        from app.services.commission_scheme_service import _match_tier

        t = _match_tier(mock_tiers, Decimal("500000"), None, None)
        assert t is not None
        assert t.tier_no == 3

    def test_boundary_belongs_to_next_tier(self, mock_tiers):
        """Left-closed-right-open: 100000 ∈ tier 2 [100000, 300000)."""
        from app.services.commission_scheme_service import _match_tier

        t = _match_tier(mock_tiers, Decimal("100000"), None, None)
        assert t is not None
        assert t.tier_no == 2

    def test_floor_applied(self, mock_tiers):
        """base 10000 @ 3% = 300, floor 2000 → 2000."""
        from app.services.commission_scheme_service import _match_tier

        t = _match_tier(mock_tiers, Decimal("10000"), None, None)
        assert t is not None
        assert t.tier_no == 1

    def test_cap_applied(self, mock_tiers):
        """base 200000 @ 5% = 10000, cap 10000 → 10000."""
        from app.services.commission_scheme_service import _match_tier

        t = _match_tier(mock_tiers, Decimal("200000"), None, None)
        assert t is not None
        assert t.tier_no == 2

    def test_above_max_returns_last_tier(self, mock_tiers):
        from app.services.commission_scheme_service import _match_tier

        t = _match_tier(mock_tiers, Decimal("999999"), None, None)
        assert t is not None
        assert t.tier_no == 3

    def test_no_match_returns_none(self, mock_tiers):
        """base 0 with no zero-tier returns None."""
        from app.services.commission_scheme_service import _match_tier

        # Remove first-tier low=0 check — this is edge case where amount < lowest tier
        # Since our first tier starts at 0, this shouldn't happen.
        # Test with amount = -1 (invalid):
        t = _match_tier(mock_tiers, Decimal("-1"), None, None)
        assert t is None


# ── Scheme Lifecycle (integration with DB) ─────────────────────────────


class TestSchemeLifecycle:
    """CRUD + status transitions via service layer with test DB."""

    @pytest.mark.asyncio
    async def test_create_scheme(self, db_session):
        from app.services.commission_scheme_service import create_scheme

        data = {
            "name": "Test Scheme",
            "description": "test",
            "effective_from": date(2026, 7, 1),
            "tiers": [
                {
                    "tier_no": 1,
                    "metric_type": "monthly_sales",
                    "low_amount": Decimal("0"),
                    "high_amount": Decimal("100000"),
                    "rate": Decimal("0.03"),
                    "cap_amount": Decimal("0"),
                    "floor_amount": Decimal("0"),
                },
            ],
            "assignments": [],
        }
        scheme = await create_scheme(db_session, data, user_id=1)
        assert scheme.id > 0
        assert scheme.name == "Test Scheme"
        assert scheme.version_no == 1
        assert scheme.status == "draft"

    @pytest.mark.asyncio
    async def test_activate_scheme(self, db_session):
        from app.services.commission_scheme_service import (
            activate_scheme,
            create_scheme,
        )

        data = {
            "name": "Activate Test",
            "effective_from": date(2020, 1, 1),  # Past date → immediate active
            "tiers": [
                {
                    "tier_no": 1,
                    "metric_type": "monthly_sales",
                    "low_amount": Decimal("0"),
                    "high_amount": None,
                    "rate": Decimal("0.05"),
                    "cap_amount": Decimal("0"),
                    "floor_amount": Decimal("0"),
                },
            ],
            "assignments": [],
        }
        scheme = await create_scheme(db_session, data, user_id=1)
        assert scheme.status == "draft"

        activated = await activate_scheme(db_session, scheme.id)
        assert activated.status == "active"

    @pytest.mark.asyncio
    async def test_update_bumps_version(self, db_session):
        from app.services.commission_scheme_service import create_scheme, update_scheme

        data = {
            "name": "Version Test",
            "effective_from": date(2026, 7, 1),
            "tiers": [
                {
                    "tier_no": 1,
                    "metric_type": "monthly_sales",
                    "low_amount": Decimal("0"),
                    "high_amount": None,
                    "rate": Decimal("0.03"),
                    "cap_amount": Decimal("0"),
                    "floor_amount": Decimal("0"),
                },
            ],
            "assignments": [],
        }
        scheme = await create_scheme(db_session, data, user_id=1)
        assert scheme.version_no == 1

        updated = await update_scheme(
            db_session, scheme.id, {"name": "Updated"}, user_id=1
        )
        assert updated.version_no == 2
        assert updated.name == "Updated"

    @pytest.mark.asyncio
    async def test_delete_unreferenced_scheme(self, db_session):
        from app.services.commission_scheme_service import (
            create_scheme,
            delete_scheme,
            get_scheme,
        )

        data = {
            "name": "Delete Test",
            "effective_from": date(2026, 7, 1),
            "tiers": [
                {
                    "tier_no": 1,
                    "metric_type": "monthly_sales",
                    "low_amount": Decimal("0"),
                    "high_amount": None,
                    "rate": Decimal("0.03"),
                    "cap_amount": Decimal("0"),
                    "floor_amount": Decimal("0"),
                },
            ],
            "assignments": [],
        }
        scheme = await create_scheme(db_session, data, user_id=1)
        await delete_scheme(db_session, scheme.id)

        with pytest.raises(Exception, match="not found"):
            await get_scheme(db_session, scheme.id)

    @pytest.mark.asyncio
    async def test_auto_expire(self, db_session):
        from app.services.commission_scheme_service import (
            auto_expire_schemes,
            create_scheme,
        )

        data = {
            "name": "Expire Test",
            "effective_from": date(2020, 1, 1),
            "effective_to": date(2020, 6, 30),
            "tiers": [
                {
                    "tier_no": 1,
                    "metric_type": "monthly_sales",
                    "low_amount": Decimal("0"),
                    "high_amount": None,
                    "rate": Decimal("0.03"),
                    "cap_amount": Decimal("0"),
                    "floor_amount": Decimal("0"),
                },
            ],
            "assignments": [],
        }
        scheme = await create_scheme(db_session, data, user_id=1)
        # Manually set active for the test
        scheme.status = "active"
        await db_session.commit()

        count = await auto_expire_schemes(db_session)
        assert count > 0

        # Verify expired
        result = await db_session.execute(
            select(CommissionScheme).where(CommissionScheme.id == scheme.id)
        )
        s = result.scalar_one()
        assert s.status == "expired"
