"""Production batch management test: delivery note shipped → batch allocation → COGS on SalesOrderItem.

Validates the batch allocation and COGS path:
1. Create two inventory batches for the same product at different costs
2. Create a sales order + delivery note
3. Ship the delivery note
4. Assert batch quantities are deducted and SalesOrderItem.cost_amount is populated
"""

import pytest
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession  # noqa: F401

from app.models.product import Inventory, InventoryBatchORM, Product, Warehouse
from app.models.sales import DeliveryNote, DeliveryNoteItem, SalesOrder, SalesOrderItem
from app.services.inventory_batch_service import inventory_batch_service
from app.services.sales_service.delivery_notes import DeliveryNoteService


pytestmark = pytest.mark.asyncio


class TestBatchManagement:
    """Production batch management: batch allocation + COGS on delivery note shipped."""

    async def _setup_product_warehouse(self, db_session: AsyncSession):
        """Create product + warehouse + two batches with different costs."""
        # Warehouse
        warehouse = Warehouse(name="POC-WH", location="POC test location")
        db_session.add(warehouse)
        await db_session.flush()

        # Product
        product = Product(name="POC-电容 10uF", sku="POC-CAP-10UF", unit="PCS")
        db_session.add(product)
        await db_session.flush()

        # Inventory aggregate
        inv = Inventory(product_id=product.id, warehouse_id=warehouse.id, quantity=0, unit_price=0)
        db_session.add(inv)
        await db_session.flush()

        # Batch A: 80 pcs @ 5.0 (older, lower cost)
        batch_a = InventoryBatchORM(
            product_id=product.id,
            warehouse_id=warehouse.id,
            batch_no="POC-B001",
            quantity=80,
            unit_cost=Decimal("5.0"),
            received_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
            expiry_date=datetime(2027, 1, 1, tzinfo=timezone.utc),
            status="available",
        )
        db_session.add(batch_a)

        # Batch B: 30 pcs @ 6.0 (newer, higher cost)
        batch_b = InventoryBatchORM(
            product_id=product.id,
            warehouse_id=warehouse.id,
            batch_no="POC-B002",
            quantity=30,
            unit_cost=Decimal("6.0"),
            received_date=datetime(2026, 2, 1, tzinfo=timezone.utc),
            expiry_date=datetime(2027, 6, 1, tzinfo=timezone.utc),
            status="available",
        )
        db_session.add(batch_b)

        # Update inventory total qty
        inv.quantity = 110
        inv.unit_price = 5.27  # weighted avg
        db_session.add(inv)
        await db_session.flush()

        return product.id, warehouse.id, batch_a.id, batch_b.id

    async def test_delivery_ships_and_cogs_is_populated(self, db_session: AsyncSession):
        """Ship 100 pcs → LCFO consumes B001(80) + B002(20) → cost_amount = 520."""
        product_id, warehouse_id, batch_a_id, batch_b_id = await self._setup_product_warehouse(db_session)

        # ── Sales Order ──────────────────────────────────────────────────────
        from app.models.customer import Customer

        customer = Customer(name="POC-测试客户")
        db_session.add(customer)
        await db_session.flush()

        order = SalesOrder(
            order_no="POC-SO-001",
            customer_id=customer.id,
            status="confirmed",
            total_amount=Decimal("1000"),
        )
        db_session.add(order)
        await db_session.flush()

        order_item = SalesOrderItem(
            order_id=order.id,
            product_id=product_id,
            product_name="POC-电容 10uF",
            quantity=100,
            unit_price=Decimal("10.0"),
            total_price=Decimal("1000"),
            cost_amount=None,  # ← should be populated after ship
        )
        db_session.add(order_item)
        await db_session.flush()

        # ── Delivery Note ────────────────────────────────────────────────────
        note = DeliveryNote(
            delivery_no="POC-DN-001",
            sales_order_id=order.id,
            customer_id=customer.id,
            status="pending",
        )
        db_session.add(note)
        await db_session.flush()

        note_item = DeliveryNoteItem(
            delivery_note_id=note.id,
            product_id=product_id,
            product_name="POC-电容 10uF",
            quantity=100,
        )
        db_session.add(note_item)
        await db_session.flush()
        # Load items relationship via async-safe refresh (avoid MissingGreenlet
        # when service later accesses note.items inside a sync for-loop).
        await db_session.refresh(note, ["items"])

        # ── Pre-check: batches have correct qty ─────────────────────────────
        b_a = await db_session.get(InventoryBatchORM, batch_a_id)
        b_b = await db_session.get(InventoryBatchORM, batch_b_id)
        assert b_a.quantity == 80
        assert b_b.quantity == 30

        # ── Ship the delivery note ───────────────────────────────────────────
        svc = DeliveryNoteService()
        await svc.update_delivery_note(
            db_session, note, {"status": "shipped"}, actor="poc-test"
        )

        # Force refresh
        await db_session.refresh(b_a)
        await db_session.refresh(b_b)
        await db_session.refresh(order_item)

        # ── Assert batch deductions ──────────────────────────────────────────
        # LCFO: B001(5.0) first → 80 pcs, then B002(6.0) → 20 pcs
        await db_session.refresh(b_a)
        await db_session.refresh(b_b)
        assert b_a.quantity == 0, f"Batch A should be 0, got {b_a.quantity}"
        assert b_a.status == "consumed"
        assert b_b.quantity == 10, f"Batch B should have 10 left, got {b_b.quantity}"

        # ── Assert COGS ──────────────────────────────────────────────────────
        # COGS = 80 × 5.0 + 20 × 6.0 = 400 + 120 = 520
        assert order_item.cost_amount is not None, "cost_amount should be populated"
        assert float(order_item.cost_amount) == pytest.approx(520.0, rel=0.01), (
            f"Expected COGS 520, got {order_item.cost_amount}"
        )

    async def test_allocate_for_delivery_returns_correct_cogs(self, db_session: AsyncSession):
        """Unit test: 100 pcs from batches 80@5 + 30@6 → LCFO COGS = 520."""
        product_id, warehouse_id, _, _ = await self._setup_product_warehouse(db_session)

        result = await inventory_batch_service.allocate_for_delivery(
            db_session,
            product_id=product_id,
            warehouse_id=warehouse_id,
            quantity=100,
            strategy="lowest_cost_first",
        )

        assert result.is_fully_allocated, "Should fully allocate 100 pcs"
        assert result.unfilled_qty == 0
        # LCFO: 80 @ 5.0 + 20 @ 6.0 = 520
        assert float(result.total_cost) == pytest.approx(520.0, rel=0.01)
        assert len(result.allocations) == 2
        assert result.allocations[0].batch_no == "POC-B001"
        assert result.allocations[0].quantity == 80
        assert result.allocations[1].batch_no == "POC-B002"
        assert result.allocations[1].quantity == 20

    async def test_unfilled_when_insufficient_stock(self, db_session: AsyncSession):
        """Request 150 pcs but only 110 available → unfilled = 40."""
        product_id, warehouse_id, _, _ = await self._setup_product_warehouse(db_session)

        result = await inventory_batch_service.allocate_for_delivery(
            db_session,
            product_id=product_id,
            warehouse_id=warehouse_id,
            quantity=150,
            strategy="lowest_cost_first",
        )

        assert not result.is_fully_allocated
        assert result.unfilled_qty == 40
        assert result.total_quantity == 110
        # COGS for 110: 80×5 + 30×6 = 400 + 180 = 580
        assert float(result.total_cost) == pytest.approx(580.0, rel=0.01)
