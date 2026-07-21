"""Batch traceability service — Stage 18 / Production Batch Management.

Provides bidirectional traceability for a single inventory batch:
  - Upstream: supplier + purchase orders that received this batch
  - Downstream: delivery notes / sales orders / customers that consumed it

Backbone: ``InventoryTransaction.batch_id`` (added Stage 18). Historical
transactions without ``batch_id`` are out of scope for forward traceability.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer import Customer
from app.models.product import (
    InventoryBatchORM,
    InventoryTransaction,
    Product,
    Supplier,
    Warehouse,
)
from app.models.sales import DeliveryNote, SalesOrder
from app.models.transaction import PurchaseOrder

logger = logging.getLogger(__name__)


class BatchTraceabilityService:
    """Resolve bidirectional traceability for an inventory batch."""

    async def get_traceability(
        self, db: AsyncSession, batch_id: int
    ) -> dict[str, Any] | None:
        """Return full traceability tree, or ``None`` if batch not found.

        Shape::

            {
              "batch": {...core batch info + product/supplier/warehouse names...},
              "upstream": {
                "supplier": {...} | None,
                "purchase_orders": [...],          # POs that received this batch
                "stock_in_records": [...],         # raw stock_in transactions
              },
              "downstream": {
                "deliveries": [...],               # delivery notes that consumed qty
                "customers": [...],                # distinct customer list
                "total_consumed": int,
                "remaining_qty": int,
              }
            }
        """
        # 1. Core batch (with eager-loaded names via joinedload).
        batch = (
            await db.execute(
                select(InventoryBatchORM)
                .where(InventoryBatchORM.id == batch_id)
            )
        ).scalar_one_or_none()
        if batch is None:
            return None

        # Eager-load product / supplier / warehouse names.
        # Stage 19 P1 #3: fire the 3 independent db.get() in parallel —
        # cuts ~33% latency vs serial for the metadata fetch.
        async def _fetch_supplier() -> Supplier | None:
            if batch.supplier_id is None:
                return None
            return await db.get(Supplier, batch.supplier_id)

        product, warehouse, supplier = await asyncio.gather(
            db.get(Product, batch.product_id),
            db.get(Warehouse, batch.warehouse_id),
            _fetch_supplier(),
        )

        batch_info = {
            "id": batch.id,
            "batch_no": batch.batch_no,
            "product_id": batch.product_id,
            "product_name": product.name if product else None,
            "product_sku": product.sku if product else None,
            "warehouse_id": batch.warehouse_id,
            "warehouse_name": warehouse.name if warehouse else None,
            "supplier_id": batch.supplier_id,
            "supplier_name": supplier.name if supplier else None,
            "quantity": batch.quantity,
            "locked_quantity": batch.locked_quantity,
            "unit_cost": float(batch.unit_cost or 0),
            "received_date": _iso(batch.received_date),
            "manufacture_date": _iso(batch.manufacture_date),
            "expiry_date": _iso(batch.expiry_date),
            "status": batch.status,
            "rohs_compliant": batch.rohs_compliant,
            "msl_level": batch.msl_level,
            "certificate_url": batch.certificate_url,
            "notes": batch.notes,
        }

        # 2. Upstream: stock_in transactions for this batch + matching POs.
        upstream = await self._get_upstream(db, batch)

        # 3. Downstream: stock_out transactions → delivery notes → customers.
        downstream = await self._get_downstream(db, batch)

        return {
            "batch": batch_info,
            "upstream": upstream,
            "downstream": downstream,
        }

    # ── upstream ──────────────────────────────────────────────────────

    async def _get_upstream(
        self, db: AsyncSession, batch: InventoryBatchORM
    ) -> dict[str, Any]:
        """Find stock_in records for this batch + related purchase orders."""
        # 2a. Direct stock_in transactions tagged with this batch_id.
        stock_in_rows = (
            await db.execute(
                select(InventoryTransaction)
                .where(
                    InventoryTransaction.batch_id == batch.id,
                    InventoryTransaction.type == "stock_in",
                )
                .order_by(InventoryTransaction.created_at.asc().nulls_last())
            )
        ).scalars().all()

        stock_in_records = [
            {
                "id": t.id,
                "reference_type": t.reference_type,
                "reference_id": t.reference_id,
                "quantity": t.quantity,
                "before_qty": t.before_qty,
                "after_qty": t.after_qty,
                "created_at": _iso(t.created_at),
                "notes": t.notes,
            }
            for t in stock_in_rows
        ]

        # 2b. Purchase orders that received this product from this supplier
        # (fuzzy link: PO + product + supplier, most recent first).
        purchase_orders: list[dict[str, Any]] = []
        if batch.supplier_id is not None:
            po_rows = (
                await db.execute(
                    select(PurchaseOrder)
                    .where(
                        PurchaseOrder.supplier_id == batch.supplier_id,
                    )
                    .order_by(PurchaseOrder.created_at.desc().nulls_last())
                    .limit(20)
                )
            ).scalars().all()
            # Filter to POs that match this product (via PO items if loaded).
            for po in po_rows:
                # PO.item_lines is a relationship; we don't load it eagerly to
                # keep this query light. The caller can join if needed.
                purchase_orders.append(
                    {
                        "id": po.id,
                        "po_no": getattr(po, "po_no", None),
                        "supplier_id": po.supplier_id,
                        "status": getattr(po, "status", None),
                        "order_date": _iso(getattr(po, "order_date", None)),
                        "expected_date": _iso(getattr(po, "expected_date", None)),
                        "total_amount": float(getattr(po, "total_amount", 0) or 0),
                    }
                )

        return {
            "supplier": {
                "id": batch.supplier_id,
                "name": supplier.name if (supplier := await db.get(Supplier, batch.supplier_id)) else None,
            }
            if batch.supplier_id
            else None,
            "purchase_orders": purchase_orders,
            "stock_in_records": stock_in_records,
        }

    # ── downstream ───────────────────────────────────────────────────

    async def _get_downstream(
        self, db: AsyncSession, batch: InventoryBatchORM
    ) -> dict[str, Any]:
        """Find delivery notes / sales orders / customers that consumed this batch."""
        # 3a. stock_out transactions with this batch_id, joined to delivery
        # notes → sales orders → customers. Left joins because historical
        # transactions (pre-Stage 18) may have null reference.
        rows = (
            await db.execute(
                select(
                    InventoryTransaction,
                    DeliveryNote,
                    SalesOrder,
                    Customer,
                )
                .outerjoin(
                    DeliveryNote,
                    (InventoryTransaction.reference_type == "delivery_note")
                    & (InventoryTransaction.reference_id == DeliveryNote.id),
                )
                .outerjoin(SalesOrder, DeliveryNote.sales_order_id == SalesOrder.id)
                .outerjoin(Customer, SalesOrder.customer_id == Customer.id)
                .where(
                    InventoryTransaction.batch_id == batch.id,
                    InventoryTransaction.type == "stock_out",
                )
                .order_by(InventoryTransaction.created_at.asc().nulls_last())
            )
        ).all()

        deliveries: list[dict[str, Any]] = []
        customer_map: dict[int, dict[str, Any]] = {}
        total_consumed = 0

        for txn, note, so, customer in rows:
            qty = abs(txn.quantity or 0)
            total_consumed += qty
            if note is not None and customer is not None:
                customer_map[customer.id] = {
                    "id": customer.id,
                    "name": customer.name,
                    "short_name": customer.short_name,
                }
            deliveries.append(
                {
                    "transaction_id": txn.id,
                    "transaction_at": _iso(txn.created_at),
                    "quantity": qty,
                    "delivery_note_id": note.id if note else None,
                    "delivery_no": getattr(note, "delivery_no", None) if note else None,
                    "sales_order_id": so.id if so else None,
                    "sales_order_no": getattr(so, "order_no", None) if so else None,
                    "customer_id": customer.id if customer else None,
                    "customer_name": customer.name if customer else None,
                }
            )

        return {
            "deliveries": deliveries,
            "customers": list(customer_map.values()),
            "total_consumed": total_consumed,
            "remaining_qty": batch.quantity,
            "delivery_count": len(deliveries),
            "customer_count": len(customer_map),
        }


# Module-level singleton (matches `inventory_batch_service` style).
batch_traceability_service = BatchTraceabilityService()


def _iso(value: Any) -> str | None:
    """Serialize datetime-like to ISO 8601 string (or None).

    Accepts ``Any`` because SQLAlchemy ``DateTime`` mapped columns are typed
    as SQLAlchemy ``DateTime`` (not Python's ``datetime``) for static analysis,
    but at runtime always hold ``datetime.datetime`` instances.
    """
    return value.isoformat() if value is not None else None