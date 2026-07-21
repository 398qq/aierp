"""Batch traceability API tests — Stage 18 / Production Batch Management.

Verifies the bidirectional traceability service:
  - Upstream: supplier + stock_in records
  - Downstream: delivery notes + customers that consumed qty from this batch
  - Edge: batch not found
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer import Customer
from app.models.product import (
    InventoryBatchORM,
    InventoryTransaction,
    Product,
    Supplier,
    Warehouse,
)
from app.models.sales import DeliveryNote, DeliveryNoteItem, SalesOrder, SalesOrderItem
from app.services.batch_traceability_service import batch_traceability_service

pytestmark = pytest.mark.asyncio


# ── helpers ─────────────────────────────────────────────────────────


async def _make_batch(
    db_session: AsyncSession,
    *,
    product_id: int,
    warehouse_id: int,
    supplier_id: int | None = None,
    quantity: int = 100,
    unit_cost: Decimal = Decimal("5.0"),
    batch_no: str = "TRACE-001",
) -> InventoryBatchORM:
    batch = InventoryBatchORM(
        product_id=product_id,
        warehouse_id=warehouse_id,
        supplier_id=supplier_id,
        batch_no=batch_no,
        quantity=quantity,
        locked_quantity=0,
        unit_cost=unit_cost,
        received_date=datetime(2026, 1, 15, tzinfo=timezone.utc),
        expiry_date=datetime(2027, 1, 15, tzinfo=timezone.utc),
        manufacture_date=datetime(2025, 12, 1, tzinfo=timezone.utc),
        status="available",
        rohs_compliant=True,
        msl_level="MSL2",
    )
    db_session.add(batch)
    await db_session.flush()
    return batch


async def _setup_basics(db_session: AsyncSession) -> dict:
    """Create supplier + customer + warehouse + product + InventoryBatchORM.

    Returns dict with all ids for test usage.
    """
    supplier = Supplier(name="测试供应商-甲")
    db_session.add(supplier)
    customer = Customer(name="测试客户-乙", level="A")
    db_session.add(customer)
    warehouse = Warehouse(name="深圳主仓", location="深圳")
    db_session.add(warehouse)
    product = Product(name="测试电容 10uF", sku="CAP-10UF-T", unit="PCS")
    db_session.add(product)
    await db_session.flush()

    batch = await _make_batch(
        db_session,
        product_id=product.id,
        warehouse_id=warehouse.id,
        supplier_id=supplier.id,
        quantity=100,
        unit_cost=Decimal("5.0"),
        batch_no="TRACE-B-001",
    )

    return {
        "supplier": supplier,
        "customer": customer,
        "warehouse": warehouse,
        "product": product,
        "batch": batch,
    }


# ── tests ───────────────────────────────────────────────────────────


class TestBatchTraceability:
    async def test_returns_none_for_missing_batch(self, db_session: AsyncSession):
        """Batch not found → returns None (API translates to 404)."""
        result = await batch_traceability_service.get_traceability(db_session, 99999)
        assert result is None

    async def test_core_batch_info(self, db_session: AsyncSession):
        """Core batch info includes product / supplier / warehouse names."""
        ctx = await _setup_basics(db_session)
        result = await batch_traceability_service.get_traceability(
            db_session, ctx["batch"].id
        )
        assert result is not None
        b = result["batch"]
        assert b["batch_no"] == "TRACE-B-001"
        assert b["quantity"] == 100
        assert b["unit_cost"] == pytest.approx(5.0)
        assert b["supplier_name"] == "测试供应商-甲"
        assert b["warehouse_name"] == "深圳主仓"
        assert b["product_name"] == "测试电容 10uF"
        assert b["status"] == "available"
        assert b["rohs_compliant"] is True
        assert b["msl_level"] == "MSL2"

    async def test_upstream_includes_supplier_and_stock_in(
        self, db_session: AsyncSession
    ):
        """Upstream section reports supplier + any stock_in transactions."""
        ctx = await _setup_basics(db_session)
        batch = ctx["batch"]

        # Add a stock_in transaction linked to this batch.
        stock_in = InventoryTransaction(
            product_id=batch.product_id,
            warehouse_id=batch.warehouse_id,
            type="stock_in",
            quantity=100,
            reference_type="purchase_order",
            reference_id=1,
            batch_id=batch.id,
            notes="PO #PO-001 received",
        )
        db_session.add(stock_in)
        await db_session.flush()

        result = await batch_traceability_service.get_traceability(
            db_session, batch.id
        )
        assert result is not None
        upstream = result["upstream"]
        assert upstream["supplier"] is not None
        assert upstream["supplier"]["name"] == "测试供应商-甲"
        assert len(upstream["stock_in_records"]) == 1
        assert upstream["stock_in_records"][0]["quantity"] == 100
        assert upstream["stock_in_records"][0]["reference_type"] == "purchase_order"

    async def test_downstream_tracks_delivery_to_customer(
        self, db_session: AsyncSession
    ):
        """Downstream resolves delivery notes + sales orders + customers."""
        ctx = await _setup_basics(db_session)
        batch = ctx["batch"]
        product = ctx["product"]
        customer = ctx["customer"]

        # Build a sales order → delivery note for this product/customer.
        order = SalesOrder(
            order_no="SO-TRACE-001",
            customer_id=customer.id,
            status="confirmed",
            total_amount=Decimal("1000"),
        )
        db_session.add(order)
        await db_session.flush()

        order_item = SalesOrderItem(
            order_id=order.id,
            product_id=product.id,
            product_name=product.name,
            quantity=10,
            unit_price=Decimal("10.0"),
            total_price=Decimal("100"),
        )
        db_session.add(order_item)

        note = DeliveryNote(
            delivery_no="DN-TRACE-001",
            sales_order_id=order.id,
            customer_id=customer.id,
            status="shipped",
        )
        db_session.add(note)
        await db_session.flush()

        note_item = DeliveryNoteItem(
            delivery_note_id=note.id,
            product_id=product.id,
            product_name=product.name,
            quantity=10,
        )
        db_session.add(note_item)
        await db_session.flush()

        # Simulate commit_deduction writing a stock_out with batch_id.
        txn = InventoryTransaction(
            product_id=product.id,
            warehouse_id=batch.warehouse_id,
            type="stock_out",
            quantity=-10,
            reference_type="delivery_note",
            reference_id=note.id,
            batch_id=batch.id,
        )
        db_session.add(txn)
        # Mirror the deduct_for_delivery batch quantity update.
        batch.quantity = 90
        await db_session.flush()

        result = await batch_traceability_service.get_traceability(
            db_session, batch.id
        )
        assert result is not None
        ds = result["downstream"]
        assert ds["total_consumed"] == 10
        assert ds["remaining_qty"] == 90
        assert ds["delivery_count"] == 1
        assert ds["customer_count"] == 1
        assert len(ds["deliveries"]) == 1
        d = ds["deliveries"][0]
        assert d["delivery_no"] == "DN-TRACE-001"
        assert d["sales_order_no"] == "SO-TRACE-001"
        assert d["customer_name"] == "测试客户-乙"
        assert d["quantity"] == 10

        # Customers list is distinct.
        assert len(ds["customers"]) == 1
        assert ds["customers"][0]["name"] == "测试客户-乙"

    async def test_downstream_multiple_customers_distinct(
        self, db_session: AsyncSession
    ):
        """Two customers consuming from same batch → customer_count=2."""
        ctx = await _setup_basics(db_session)
        batch = ctx["batch"]
        product = ctx["product"]

        # Add a second customer.
        customer_b = Customer(name="测试客户-丙", level="B")
        db_session.add(customer_b)
        await db_session.flush()

        # Customer A: order → note → consume 5.
        order_a = SalesOrder(
            order_no="SO-A", customer_id=ctx["customer"].id,
            status="confirmed", total_amount=Decimal("500"),
        )
        db_session.add(order_a)
        await db_session.flush()  # populate order_a.id before referencing in note
        note_a = DeliveryNote(
            delivery_no="DN-A", sales_order_id=order_a.id,
            customer_id=ctx["customer"].id, status="shipped",
        )
        db_session.add(note_a)
        await db_session.flush()
        db_session.add(DeliveryNoteItem(delivery_note_id=note_a.id, product_id=product.id, product_name=product.name, quantity=5))
        db_session.add(InventoryTransaction(
            product_id=product.id, warehouse_id=batch.warehouse_id,
            type="stock_out", quantity=-5,
            reference_type="delivery_note", reference_id=note_a.id,
            batch_id=batch.id,
        ))

        # Customer B: order → note → consume 3.
        order_b = SalesOrder(
            order_no="SO-B", customer_id=customer_b.id,
            status="confirmed", total_amount=Decimal("300"),
        )
        db_session.add(order_b)
        await db_session.flush()  # populate order_b.id before referencing in note
        note_b = DeliveryNote(
            delivery_no="DN-B", sales_order_id=order_b.id,
            customer_id=customer_b.id, status="shipped",
        )
        db_session.add(note_b)
        await db_session.flush()
        db_session.add(DeliveryNoteItem(delivery_note_id=note_b.id, product_id=product.id, product_name=product.name, quantity=3))
        db_session.add(InventoryTransaction(
            product_id=product.id, warehouse_id=batch.warehouse_id,
            type="stock_out", quantity=-3,
            reference_type="delivery_note", reference_id=note_b.id,
            batch_id=batch.id,
        ))

        batch.quantity = 92  # 100 - 5 - 3
        await db_session.flush()

        result = await batch_traceability_service.get_traceability(
            db_session, batch.id
        )
        assert result is not None
        ds = result["downstream"]
        assert ds["total_consumed"] == 8
        assert ds["remaining_qty"] == 92
        assert ds["delivery_count"] == 2
        assert ds["customer_count"] == 2
        customer_names = {c["name"] for c in ds["customers"]}
        assert customer_names == {"测试客户-乙", "测试客户-丙"}

    async def test_no_downstream_returns_empty(self, db_session: AsyncSession):
        """Batch with no stock_out transactions → empty downstream."""
        ctx = await _setup_basics(db_session)
        result = await batch_traceability_service.get_traceability(
            db_session, ctx["batch"].id
        )
        assert result is not None
        ds = result["downstream"]
        assert ds["deliveries"] == []
        assert ds["customers"] == []
        assert ds["total_consumed"] == 0
        assert ds["remaining_qty"] == 100
        assert ds["delivery_count"] == 0
        assert ds["customer_count"] == 0