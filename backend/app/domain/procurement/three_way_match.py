"""Procurement domain — three-way match (PO / GR / Invoice).

Three-way match is the cornerstone of accounts-payable fraud prevention:
a supplier invoice is only paid when it matches BOTH the original
purchase order AND the goods receipt.

This module owns the matching logic and the rules that govern it.
The persistence layer (GoodsReceipt, GoodsReceiptLine) lives in
app/models/transaction.py alongside the related PO tables.
"""

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import List



class MatchStatus(str, Enum):
    """Outcome of a three-way match attempt."""

    MATCHED = "matched"               # All three sides agree within tolerance
    QTY_MISMATCH = "qty_mismatch"     # GR qty != invoice qty
    PRICE_MISMATCH = "price_mismatch" # PO price != invoice price
    BOTH_MISMATCH = "both_mismatch"   # Both qty and price differ
    MISSING_PO = "missing_po"         # Invoice has no matching PO
    MISSING_GR = "missing_gr"         # Invoice has no matching goods receipt
    DUPLICATE = "duplicate"           # Invoice already matched against this PO


class MatchTolerance:
    """Default tolerance values for 3-way match.

    Configurable in production: amount tolerance is usually 0.1% or
    ¥1 (whichever is greater) to absorb FX rounding.
    """

    AMOUNT_TOLERANCE_ABS = Decimal("1.00")       # ¥1 absolute
    AMOUNT_TOLERANCE_PCT = Decimal("0.001")      # 0.1% relative
    QTY_TOLERANCE = Decimal("0")                # Exact qty match required

    @classmethod
    def within_tolerance(cls, expected: Decimal, actual: Decimal) -> bool:
        diff = abs(expected - actual)
        if diff <= cls.AMOUNT_TOLERANCE_ABS:
            return True
        if expected > 0 and diff / expected <= cls.AMOUNT_TOLERANCE_PCT:
            return True
        return False


@dataclass
class POLineSnapshot:
    """Read-only snapshot of a purchase-order line for matching."""

    product_id: int
    quantity: int
    unit_price: Decimal


@dataclass
class GRLineSnapshot:
    """Read-only snapshot of a goods-receipt line for matching."""

    product_id: int
    quantity_received: int
    unit_cost: Decimal  # Sometimes differs from PO price due to freight/duty


@dataclass
class InvoiceLineSnapshot:
    """Read-only snapshot of a supplier-invoice line for matching."""

    product_id: int
    quantity: int
    unit_price: Decimal
    amount: Decimal  # Pre-computed line total (qty * unit_price +/- adjustments)


@dataclass
class LineDiscrepancy:
    """One mismatch detail, captured for the AP clerk's review."""

    product_id: int
    discrepancy_type: str   # "qty" | "price" | "amount"
    expected: Decimal
    actual: Decimal
    variance: Decimal


@dataclass
class ThreeWayMatchResult:
    """Outcome of matching a supplier invoice against PO + GR."""

    status: MatchStatus
    invoice_total: Decimal
    po_total: Decimal
    gr_total: Decimal
    discrepancies: List[LineDiscrepancy] = field(default_factory=list)
    notes: str = ""

    @property
    def is_matched(self) -> bool:
        return self.status == MatchStatus.MATCHED

    @property
    def requires_clerk_review(self) -> bool:
        return self.status in (
            MatchStatus.QTY_MISMATCH,
            MatchStatus.PRICE_MISMATCH,
            MatchStatus.BOTH_MISMATCH,
        )


def _discrepancy_total(
    discrepancies: List[LineDiscrepancy],
) -> Decimal:
    return sum((d.variance for d in discrepancies), Decimal("0"))


def match_po_gr_invoice(
    po_lines: List[POLineSnapshot],
    gr_lines: List[GRLineSnapshot],
    invoice_lines: List[InvoiceLineSnapshot],
    existing_matches: int = 0,
) -> ThreeWayMatchResult:
    """Perform three-way match: PO ↔ GR ↔ Invoice.

    Args:
        po_lines: Purchase order lines
        gr_lines: Goods receipt lines (subset or superset of PO qty)
        invoice_lines: Supplier invoice lines to validate
        existing_matches: How many invoices have already been matched
            against this PO. > 0 means duplicate.

    Returns:
        ThreeWayMatchResult describing whether the invoice can be
        auto-approved or needs human review.
    """
    if existing_matches > 0:
        return ThreeWayMatchResult(
            status=MatchStatus.DUPLICATE,
            invoice_total=sum((line.amount for line in invoice_lines), Decimal("0")),
            po_total=Decimal("0"),
            gr_total=Decimal("0"),
            notes=f"PO already has {existing_matches} matched invoice(s)",
        )

    if not po_lines:
        return ThreeWayMatchResult(
            status=MatchStatus.MISSING_PO,
            invoice_total=sum((line.amount for line in invoice_lines), Decimal("0")),
            po_total=Decimal("0"),
            gr_total=sum(
                (line.quantity_received * line.unit_cost for line in gr_lines), Decimal("0")
            ),
            notes="No matching purchase order found",
        )

    if not gr_lines:
        return ThreeWayMatchResult(
            status=MatchStatus.MISSING_GR,
            invoice_total=sum((line.amount for line in invoice_lines), Decimal("0")),
            po_total=sum(
                (line.quantity * line.unit_price for line in po_lines), Decimal("0")
            ),
            gr_total=Decimal("0"),
            notes="No goods receipt has been recorded for this PO",
        )

    # Build lookup maps by product_id
    po_map: dict[int, POLineSnapshot] = {line.product_id: line for line in po_lines}
    gr_map: dict[int, GRLineSnapshot] = {line.product_id: line for line in gr_lines}

    discrepancies: List[LineDiscrepancy] = []
    qty_mismatch = False
    price_mismatch = False

    for inv_line in invoice_lines:
        pid = inv_line.product_id
        po = po_map.get(pid)
        gr = gr_map.get(pid)

        # QTY CHECK: invoice qty must equal GR qty
        if gr is None or inv_line.quantity != gr.quantity_received:
            qty_mismatch = True
            discrepancies.append(LineDiscrepancy(
                product_id=pid,
                discrepancy_type="qty",
                expected=Decimal(gr.quantity_received if gr else 0),
                actual=Decimal(inv_line.quantity),
                variance=Decimal(inv_line.quantity) - Decimal(gr.quantity_received if gr else 0),
            ))

        # PRICE CHECK: invoice unit price within tolerance of PO unit price
        if po is None:
            price_mismatch = True
            discrepancies.append(LineDiscrepancy(
                product_id=pid,
                discrepancy_type="price",
                expected=Decimal("0"),
                actual=inv_line.unit_price,
                variance=inv_line.unit_price,
            ))
        elif not MatchTolerance.within_tolerance(po.unit_price, inv_line.unit_price):
            price_mismatch = True
            discrepancies.append(LineDiscrepancy(
                product_id=pid,
                discrepancy_type="price",
                expected=po.unit_price,
                actual=inv_line.unit_price,
                variance=inv_line.unit_price - po.unit_price,
            ))

    # Totals
    invoice_total = sum((line.amount for line in invoice_lines), Decimal("0"))
    po_total = sum(
        (line.quantity * line.unit_price for line in po_lines), Decimal("0")
    )
    gr_total = sum(
        (line.quantity_received * line.unit_cost for line in gr_lines), Decimal("0")
    )

    if qty_mismatch and price_mismatch:
        status = MatchStatus.BOTH_MISMATCH
    elif qty_mismatch:
        status = MatchStatus.QTY_MISMATCH
    elif price_mismatch:
        status = MatchStatus.PRICE_MISMATCH
    else:
        status = MatchStatus.MATCHED

    notes = ""
    if status == MatchStatus.MATCHED:
        notes = "All three sides agree within tolerance"
    elif discrepancies:
        notes = (
            f"{len(discrepancies)} line discrepancies, "
            f"total variance {_discrepancy_total(discrepancies)}"
        )

    return ThreeWayMatchResult(
        status=status,
        invoice_total=invoice_total,
        po_total=po_total,
        gr_total=gr_total,
        discrepancies=discrepancies,
        notes=notes,
    )
