"""Batch expiry scheduled job tests — Stage 18 P3.

Verifies the daily ``_check_batch_expiry`` scheduler job:
  - Notifies for batches in 'expired' + '7d' buckets
  - Skips 30d / 90d buckets (separate job later)
  - Handles empty result cleanly
  - Notification content includes batch_no + days + qty + expiry

Note: the job uses ``app.database.async_session()`` (production session).
We monkey-patch it per-test so the job reads from the test DB fixture
(``db_session``) instead. Also create user id=1 to satisfy the FK
constraint (production code hardcodes admin user id=1 — see TODO).
"""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.finance import Notification
from app.models.product import InventoryBatchORM, Product, Warehouse
from app.models.user import User

pytestmark = pytest.mark.asyncio


# ── helpers ─────────────────────────────────────────────────────────


@asynccontextmanager
async def _session_cm(db: AsyncSession):
    """Async context manager yielding the provided session."""
    yield db


async def _patched_session(db: AsyncSession, monkeypatch):
    """Make ``scheduler.async_session()`` return the test session.

    Must patch the scheduler module's reference (not app.database) because
    scheduler did ``from app.database import async_session`` at import time,
    creating a separate binding in its own namespace.
    """
    from app.jobs import scheduler

    monkeypatch.setattr(scheduler, "async_session", lambda: _session_cm(db))


async def _ensure_admin_user(db: AsyncSession) -> User:
    """Create user id=1 (the admin that the job notifies).

    Production code hardcodes ``user_id=1`` (see TODO in
    ``_check_batch_expiry``). Tests must satisfy the FK constraint.
    """
    user = User(
        id=1,
        username="admin",
        password="***",
        is_active=True,
    )
    db.add(user)
    await db.flush()
    return user


async def _make_warehouse(db: AsyncSession) -> Warehouse:
    wh = Warehouse(name="预警测试仓", location="深圳")
    db.add(wh)
    await db.flush()
    return wh


async def _make_product(db: AsyncSession) -> Product:
    p = Product(name="预警测试产品", sku="EXPIRY-001", unit="PCS")
    db.add(p)
    await db.flush()
    return p


async def _make_batch(
    db: AsyncSession,
    *,
    product_id: int,
    warehouse_id: int,
    days_until_expiry: int | None,
    quantity: int = 10,
) -> InventoryBatchORM:
    expiry = None
    if days_until_expiry is not None:
        expiry = datetime.now(timezone.utc) + timedelta(days=days_until_expiry)
    batch = InventoryBatchORM(
        product_id=product_id,
        warehouse_id=warehouse_id,
        batch_no=f"E-{uuid.uuid4().hex[:8]}",
        quantity=quantity,
        expiry_date=expiry,
        status="available",
    )
    db.add(batch)
    await db.flush()
    return batch


async def _get_notifications(
    db: AsyncSession, *, related_id: int | None = None, type_: str | None = None
) -> list[Notification]:
    stmt = select(Notification).where(Notification.deleted_at.is_(None))
    if related_id is not None:
        stmt = stmt.where(Notification.related_id == related_id)
    if type_ is not None:
        stmt = stmt.where(Notification.type == type_)
    return (await db.execute(stmt)).scalars().all()


# ── tests ───────────────────────────────────────────────────────────


class TestBatchExpiryJob:
    async def test_no_notifications_when_no_expiring_batches(
        self, db_session: AsyncSession, monkeypatch
    ):
        """Empty scan result → no notifications created."""
        from app.jobs.scheduler import _check_batch_expiry

        await _ensure_admin_user(db_session)
        await _patched_session(db_session, monkeypatch)
        await _check_batch_expiry()
        notifs = await _get_notifications(db_session, type_="batch_expiry_warning")
        assert notifs == []

    async def test_notifies_expired_batch(
        self, db_session: AsyncSession, monkeypatch
    ):
        """A batch past its expiry date → 1 notification with '已过期' title."""
        from app.jobs.scheduler import _check_batch_expiry

        await _ensure_admin_user(db_session)
        wh = await _make_warehouse(db_session)
        product = await _make_product(db_session)
        batch = await _make_batch(
            db_session,
            product_id=product.id, warehouse_id=wh.id,
            days_until_expiry=-3, quantity=20,
        )

        await _patched_session(db_session, monkeypatch)
        await _check_batch_expiry()

        notifs = await _get_notifications(
            db_session, related_id=batch.id, type_="batch_expiry_warning"
        )
        assert len(notifs) == 1
        n = notifs[0]
        assert n.user_id == 1
        assert "已过期" in n.title
        assert "3" in n.title  # absolute value of -3
        assert f"产品 ID: {product.id}" in n.content
        assert "剩余: 20" in n.content

    async def test_notifies_7d_batch(
        self, db_session: AsyncSession, monkeypatch
    ):
        """Batch expiring within 7 days → 1 notification with '天内到期' title."""
        from app.jobs.scheduler import _check_batch_expiry

        await _ensure_admin_user(db_session)
        wh = await _make_warehouse(db_session)
        product = await _make_product(db_session)
        batch = await _make_batch(
            db_session,
            product_id=product.id, warehouse_id=wh.id,
            days_until_expiry=4, quantity=5,
        )

        await _patched_session(db_session, monkeypatch)
        await _check_batch_expiry()

        notifs = await _get_notifications(
            db_session, related_id=batch.id, type_="batch_expiry_warning"
        )
        assert len(notifs) == 1
        assert "4 天内到期" in notifs[0].title
        assert "剩余: 5" in notifs[0].content

    async def test_skips_30d_and_90d_buckets(
        self, db_session: AsyncSession, monkeypatch
    ):
        """Batches in 30d / 90d buckets → no notifications (separate job)."""
        from app.jobs.scheduler import _check_batch_expiry

        await _ensure_admin_user(db_session)
        wh = await _make_warehouse(db_session)
        product = await _make_product(db_session)
        batch_30 = await _make_batch(
            db_session, product_id=product.id, warehouse_id=wh.id,
            days_until_expiry=20, quantity=10,
        )
        batch_90 = await _make_batch(
            db_session, product_id=product.id, warehouse_id=wh.id,
            days_until_expiry=60, quantity=10,
        )

        await _patched_session(db_session, monkeypatch)
        await _check_batch_expiry()

        for batch in (batch_30, batch_90):
            notifs = await _get_notifications(
                db_session, related_id=batch.id, type_="batch_expiry_warning"
            )
            assert notifs == [], f"batch {batch.id} (30d/90d) should NOT be notified"

    async def test_mixed_buckets_correctly_filtered(
        self, db_session: AsyncSession, monkeypatch
    ):
        """Mixed buckets: only expired + 7d get notifications."""
        from app.jobs.scheduler import _check_batch_expiry

        await _ensure_admin_user(db_session)
        wh = await _make_warehouse(db_session)
        product = await _make_product(db_session)
        b_expired = await _make_batch(
            db_session, product_id=product.id, warehouse_id=wh.id,
            days_until_expiry=-5, quantity=3,
        )
        b_7d = await _make_batch(
            db_session, product_id=product.id, warehouse_id=wh.id,
            days_until_expiry=2, quantity=4,
        )
        b_30d = await _make_batch(
            db_session, product_id=product.id, warehouse_id=wh.id,
            days_until_expiry=15, quantity=5,
        )

        await _patched_session(db_session, monkeypatch)
        await _check_batch_expiry()

        for b, should_notify in [
            (b_expired, True),
            (b_7d, True),
            (b_30d, False),
        ]:
            notifs = await _get_notifications(
                db_session, related_id=b.id, type_="batch_expiry_warning"
            )
            if should_notify:
                assert len(notifs) == 1, f"batch {b.id} should be notified"
            else:
                assert notifs == [], f"batch {b.id} should NOT be notified"

    async def test_skips_consumed_batches(
        self, db_session: AsyncSession, monkeypatch
    ):
        """status=consumed batches are excluded by expiry_alert_service.scan()."""
        from app.jobs.scheduler import _check_batch_expiry

        await _ensure_admin_user(db_session)
        wh = await _make_warehouse(db_session)
        product = await _make_product(db_session)
        batch = await _make_batch(
            db_session, product_id=product.id, warehouse_id=wh.id,
            days_until_expiry=-2, quantity=0,
        )
        batch.status = "consumed"
        await db_session.flush()

        await _patched_session(db_session, monkeypatch)
        await _check_batch_expiry()

        notifs = await _get_notifications(
            db_session, related_id=batch.id, type_="batch_expiry_warning"
        )
        assert notifs == []