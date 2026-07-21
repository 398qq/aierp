"""Batch recall service tests — Stage 18 / Production Batch Management.

Verifies:
  - get_impact: returns None for missing batch, surfaces affected customers
  - recall_batch: marks status, freezes remaining inventory, captures actor
  - error paths: empty reason, missing batch, already-recalled idempotency
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer import Customer
from app.models.product import InventoryBatchORM, Product, Warehouse
from app.models.sales import DeliveryNote, DeliveryNoteItem, SalesOrder, SalesOrderItem
from app.services.batch_recall_service import (
    BatchRecallError,
    batch_recall_service,
)

pytestmark = pytest.mark.asyncio


# ── helpers ─────────────────────────────────────────────────────────


async def _make_warehouse(db: AsyncSession, name: str = "深圳主仓") -> Warehouse:
    wh = Warehouse(name=name, location="深圳")
    db.add(wh)
    await db.flush()
    return wh


async def _make_customer(db: AsyncSession, name: str = "召回客户A") -> Customer:
    c = Customer(name=name, level="A")
    db.add(c)
    await db.flush()
    return c


async def _make_product(db: AsyncSession) -> Product:
    p = Product(name="召回测试产品", sku="RECALL-001", unit="PCS")
    db.add(p)
    await db.flush()
    return p


async def _make_batch(
    db: AsyncSession,
    *,
    product_id: int,
    warehouse_id: int,
    quantity: int = 100,
) -> InventoryBatchORM:
    batch = InventoryBatchORM(
        product_id=product_id,
        warehouse_id=warehouse_id,
        batch_no=f"R-{uuid.uuid4().hex[:8]}",
        quantity=quantity,
        locked_quantity=0,
        status="available",
    )
    db.add(batch)
    await db.flush()
    return batch


async def _seed_consumption(
    db: AsyncSession,
    *,
    batch: InventoryBatchORM,
    product: Product,
    customer: Customer,
    qty: int,
) -> tuple[SalesOrder, DeliveryNote]:
    """Create sales order + delivery note + stock_out txn (mirrors commit_deduction)."""
    from app.models.product import InventoryTransaction

    order = SalesOrder(
        order_no=f"SO-{uuid.uuid4().hex[:6]}",
        customer_id=customer.id,
        status="confirmed",
        total_amount=qty * 10,
    )
    db.add(order)
    await db.flush()

    db.add(SalesOrderItem(
        order_id=order.id, product_id=product.id,
        product_name=product.name, quantity=qty,
        unit_price=10, total_price=qty * 10,
    ))

    note = DeliveryNote(
        delivery_no=f"DN-{uuid.uuid4().hex[:6]}",
        sales_order_id=order.id, customer_id=customer.id, status="shipped",
    )
    db.add(note)
    await db.flush()

    db.add(DeliveryNoteItem(
        delivery_note_id=note.id, product_id=product.id,
        product_name=product.name, quantity=qty,
    ))

    # Mirror commit_deduction: stock_out + batch quantity reduction
    batch.quantity = max(0, batch.quantity - qty)
    db.add(InventoryTransaction(
        product_id=product.id, warehouse_id=batch.warehouse_id,
        type="stock_out", quantity=-qty,
        reference_type="delivery_note", reference_id=note.id,
        batch_id=batch.id,
    ))
    await db.flush()
    return order, note


# ── tests ───────────────────────────────────────────────────────────


class TestBatchRecallImpact:
    async def test_impact_returns_none_for_missing_batch(
        self, db_session: AsyncSession
    ):
        """Non-existent batch → None (API translates to 404)."""
        result = await batch_recall_service.get_impact(db_session, 99999)
        assert result is None

    async def test_impact_lists_affected_customers(
        self, db_session: AsyncSession
    ):
        """After consumption, impact shows the customer + delivery count."""
        wh = await _make_warehouse(db_session)
        product = await _make_product(db_session)
        customer = await _make_customer(db_session)
        batch = await _make_batch(
            db_session, product_id=product.id, warehouse_id=wh.id, quantity=80
        )
        await _seed_consumption(
            db_session, batch=batch, product=product,
            customer=customer, qty=20,
        )

        impact = await batch_recall_service.get_impact(db_session, batch.id)
        assert impact is not None
        assert impact["customer_count"] == 1
        assert impact["delivery_count"] == 1
        assert impact["total_quantity_consumed"] == 20
        assert impact["frozen_remaining"] == 60
        assert len(impact["affected_customers"]) == 1
        assert impact["affected_customers"][0]["name"] == "召回客户A"


class TestBatchRecallExecute:
    async def test_recall_marks_status_and_freezes_remaining(
        self, db_session: AsyncSession
    ):
        """Recall sets status=recalled + locked_quantity ≥ remaining qty."""
        wh = await _make_warehouse(db_session)
        product = await _make_product(db_session)
        batch = await _make_batch(
            db_session, product_id=product.id, warehouse_id=wh.id, quantity=100
        )
        await _seed_consumption(
            db_session, batch=batch, product=product,
            customer=await _make_customer(db_session, "C1"), qty=30,
        )
        # batch.quantity should now be 70

        result = await batch_recall_service.recall_batch(
            db_session, batch.id,
            reason="质量问题：批次检测不达标",
            actor="quality-team",
        )
        assert result["batch"]["status"] == "recalled"
        assert result["frozen_remaining"] == 70
        assert result["recall"]["actor"] == "quality-team"
        assert result["recall"]["previous_status"] == "available"

        # Re-fetch and confirm DB state
        await db_session.refresh(batch)
        assert batch.status == "recalled"
        assert batch.locked_quantity >= 70

    async def test_recall_does_not_double_freeze(
        self, db_session: AsyncSession
    ):
        """locked_quantity should not exceed remaining qty (no compound freeze)."""
        wh = await _make_warehouse(db_session)
        product = await _make_product(db_session)
        batch = await _make_batch(
            db_session, product_id=product.id, warehouse_id=wh.id, quantity=50
        )

        await batch_recall_service.recall_batch(
            db_session, batch.id, reason="test", actor="qa"
        )
        await db_session.refresh(batch)
        first_locked = batch.locked_quantity
        # locked should be ≥ remaining (50) and not some larger runaway value
        assert first_locked == 50

    async def test_recall_idempotency_rejects_double_recall(
        self, db_session: AsyncSession
    ):
        """Second recall on same batch → BatchRecallError."""
        wh = await _make_warehouse(db_session)
        product = await _make_product(db_session)
        batch = await _make_batch(
            db_session, product_id=product.id, warehouse_id=wh.id, quantity=10
        )
        await batch_recall_service.recall_batch(
            db_session, batch.id, reason="first", actor="qa"
        )
        with pytest.raises(BatchRecallError, match="已处于 recalled"):
            await batch_recall_service.recall_batch(
                db_session, batch.id, reason="second", actor="qa"
            )

    async def test_recall_rejects_empty_reason(
        self, db_session: AsyncSession
    ):
        """Empty reason → BatchRecallError (recall must be audit-justified)."""
        wh = await _make_warehouse(db_session)
        product = await _make_product(db_session)
        batch = await _make_batch(
            db_session, product_id=product.id, warehouse_id=wh.id, quantity=10
        )
        with pytest.raises(BatchRecallError, match="原因不能为空"):
            await batch_recall_service.recall_batch(
                db_session, batch.id, reason="", actor="qa"
            )
        with pytest.raises(BatchRecallError, match="原因不能为空"):
            await batch_recall_service.recall_batch(
                db_session, batch.id, reason="   ", actor="qa"
            )

    async def test_recall_missing_batch_raises(
        self, db_session: AsyncSession
    ):
        """Recall on non-existent batch → BatchRecallError."""
        with pytest.raises(BatchRecallError, match="不存在"):
            await batch_recall_service.recall_batch(
                db_session, 99999, reason="test", actor="qa"
            )

    async def test_recall_full_workflow_with_multiple_customers(
        self, db_session: AsyncSession
    ):
        """End-to-end: 2 customers consume from same batch → recall surfaces both."""
        wh = await _make_warehouse(db_session)
        product = await _make_product(db_session)
        c1 = await _make_customer(db_session, "客户甲")
        c2 = await _make_customer(db_session, "客户乙")
        batch = await _make_batch(
            db_session, product_id=product.id, warehouse_id=wh.id, quantity=200
        )
        await _seed_consumption(
            db_session, batch=batch, product=product, customer=c1, qty=40,
        )
        await _seed_consumption(
            db_session, batch=batch, product=product, customer=c2, qty=30,
        )

        result = await batch_recall_service.recall_batch(
            db_session, batch.id,
            reason="供应商召回通知 #SUP-2026-07",
            actor="compliance",
        )
        assert result["customer_count"] == 2
        assert result["delivery_count"] == 2
        assert result["total_quantity_consumed"] == 70
        assert result["frozen_remaining"] == 130
        customer_names = {c["name"] for c in result["affected_customers"]}
        assert customer_names == {"客户甲", "客户乙"}
        assert result["recall"]["previous_status"] == "available"