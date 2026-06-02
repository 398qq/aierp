"""Procurement use cases — three-way match orchestration.

Maps a SupplierInvoice against its PurchaseOrder and GoodsReceipt to
either auto-approve the invoice for payment or surface discrepancies
for AP-clerk review.
"""

import logging
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.procurement.three_way_match import (
    GRLineSnapshot,
    InvoiceLineSnapshot,
    LineDiscrepancy,
    POLineSnapshot,
    match_po_gr_invoice,
)
from app.models.transaction import (
    GoodsReceipt,
    PurchaseOrder,
    SupplierInvoice,
)

logger = logging.getLogger(__name__)


def _discrepancies_to_json(discs: list[LineDiscrepancy]) -> str:
    """Serialize discrepancies to a JSON string for the DB column."""
    import json
    return json.dumps(
        [
            {
                "product_id": d.product_id,
                "type": d.discrepancy_type,
                "expected": float(d.expected),
                "actual": float(d.actual),
                "variance": float(d.variance),
            }
            for d in discs
        ],
        ensure_ascii=False,
    )


class MatchSupplierInvoiceUseCase:
    """Run 3-way match for a supplier invoice.

    Loads PO + GR + invoice, builds domain snapshots, runs the match,
    persists the result (match_status + discrepancies + matched_at)
    on the SupplierInvoice row. The matched amount drives the AP
    payment run.
    """

    def __init__(self, session: AsyncSession, user_id: int) -> None:
        self._session = session
        self._user_id = user_id

    async def execute(self, invoice_id: int) -> SupplierInvoice:
        # 1. Load invoice
        stmt = (
            select(SupplierInvoice)
            .where(
                SupplierInvoice.id == invoice_id,
                SupplierInvoice.deleted_at.is_(None),
            )
        )
        inv = (await self._session.execute(stmt)).scalar_one_or_none()
        if inv is None:
            from app.domain.shared.errors import NotFoundError
            raise NotFoundError(
                f"供应商发票 {invoice_id} 不存在",
                invoice_id=invoice_id,
            )

        # 2. Check duplicate (already matched against same PO)
        existing_matches = 0
        if inv.purchase_order_id:
            existing_matches = await self._count_matched_invoices(inv.purchase_order_id, exclude_id=inv.id)

        # 3. Load PO + items
        po_lines: list[POLineSnapshot] = []
        po_total = Decimal("0")
        if inv.purchase_order_id:
            po = (await self._session.execute(
                select(PurchaseOrder)
                .where(PurchaseOrder.id == inv.purchase_order_id)
                .options(selectinload(PurchaseOrder.items))
            )).scalar_one_or_none()
            if po:
                for item in po.items:
                    po_lines.append(POLineSnapshot(
                        product_id=item.product_id,
                        quantity=item.quantity,
                        unit_price=Decimal(str(item.unit_price or 0)),
                    ))
                    po_total += Decimal(str(item.quantity)) * Decimal(str(item.unit_price or 0))

        # 4. Load GR + items
        gr_lines: list[GRLineSnapshot] = []
        gr_total = Decimal("0")
        gr_id: int | None = inv.goods_receipt_id
        if gr_id is None and inv.purchase_order_id:
            # Auto-pick the most recent GR for this PO
            gr = (await self._session.execute(
                select(GoodsReceipt)
                .where(
                    GoodsReceipt.purchase_order_id == inv.purchase_order_id,
                    GoodsReceipt.deleted_at.is_(None),
                )
                .options(selectinload(GoodsReceipt.items))
                .order_by(GoodsReceipt.received_date.desc())
                .limit(1)
            )).scalar_one_or_none()
            if gr:
                gr_id = gr.id
        if gr_id:
            gr = (await self._session.execute(
                select(GoodsReceipt)
                .where(GoodsReceipt.id == gr_id)
                .options(selectinload(GoodsReceipt.items))
            )).scalar_one_or_none()
            if gr:
                for item in gr.items:
                    gr_lines.append(GRLineSnapshot(
                        product_id=item.product_id,
                        quantity_received=item.quantity_received,
                        unit_cost=Decimal(str(item.unit_cost or 0)),
                    ))
                    gr_total += Decimal(item.quantity_received) * Decimal(str(item.unit_cost or 0))

        # 5. Build invoice line snapshots from the invoice total
        # (line items are not stored separately for SupplierInvoice;
        # we synthesize them from PO+GR line lists)
        invoice_lines: list[InvoiceLineSnapshot] = []
        if po_lines and gr_lines:
            # Use PO product list as the canonical set of expected lines
            seen: set[int] = set()
            for po_line in po_lines:
                if po_line.product_id in seen:
                    continue
                seen.add(po_line.product_id)
                gr_line = next(
                    (g for g in gr_lines if g.product_id == po_line.product_id),
                    None,
                )
                qty = gr_line.quantity_received if gr_line else po_line.quantity
                # Allocate invoice total proportionally to PO amount
                po_subtotal = po_line.quantity * po_line.unit_price
                if po_total > 0:
                    line_amount = inv.amount * (po_subtotal / po_total)
                else:
                    line_amount = inv.amount / len(po_lines)
                invoice_lines.append(InvoiceLineSnapshot(
                    product_id=po_line.product_id,
                    quantity=int(qty),
                    unit_price=po_line.unit_price,  # use PO price as reference
                    amount=line_amount.quantize(Decimal("0.01")),
                ))

        # 6. Run match
        result = match_po_gr_invoice(
            po_lines=po_lines,
            gr_lines=gr_lines,
            invoice_lines=invoice_lines,
            existing_matches=existing_matches,
        )

        # 7. Persist result
        from datetime import datetime, timezone
        inv.match_status = result.status.value
        inv.match_discrepancies = _discrepancies_to_json(result.discrepancies)
        inv.matched_at = datetime.now(timezone.utc)
        inv.matched_by = self._user_id
        inv.goods_receipt_id = gr_id  # backfill if auto-discovered

        # If matched, mark as approved (ready for payment)
        if result.is_matched:
            inv.status = "approved"
        else:
            inv.status = "pending"  # Clerk review needed

        logger.info(
            "3-way match for SupplierInvoice #%s: %s (PO=%s, GR=%s, inv=%s, discrepancies=%d)",
            invoice_id, result.status.value, po_total, gr_total, inv.amount,
            len(result.discrepancies),
        )

        await self._session.flush()
        return inv

    async def _count_matched_invoices(self, po_id: int, exclude_id: int) -> int:
        from sqlalchemy import func
        result = await self._session.execute(
            select(func.count(SupplierInvoice.id)).where(
                SupplierInvoice.purchase_order_id == po_id,
                SupplierInvoice.deleted_at.is_(None),
                SupplierInvoice.id != exclude_id,
                SupplierInvoice.match_status.in_(["matched", "approved"]),
            )
        )
        return int(result.scalar() or 0)
