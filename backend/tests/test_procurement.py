"""Procurement domain unit tests — three-way match pure logic.

Tests the ``match_po_gr_invoice`` orchestration in isolation. No DB,
no FastAPI. The application-layer use case (`app.application.procurement.
three_way_match`) just delegates to this domain function.
"""

from decimal import Decimal


from app.domain.procurement.three_way_match import (
    GRLineSnapshot,
    InvoiceLineSnapshot,
    MatchStatus,
    MatchTolerance,
    POLineSnapshot,
    match_po_gr_invoice,
)


def _po(pid: int, qty: int = 10, price: Decimal = Decimal("10.00")) -> POLineSnapshot:
    return POLineSnapshot(product_id=pid, quantity=qty, unit_price=price)


def _gr(pid: int, qty: int = 10, cost: Decimal = Decimal("10.00")) -> GRLineSnapshot:
    return GRLineSnapshot(product_id=pid, quantity_received=qty, unit_cost=cost)


def _inv(pid: int, qty: int = 10, price: Decimal = Decimal("10.00"),
         amount: Decimal = Decimal("100.00")) -> InvoiceLineSnapshot:
    return InvoiceLineSnapshot(
        product_id=pid, quantity=qty, unit_price=price, amount=amount,
    )


class TestMatchTolerance:
    def test_within_tolerance_exact(self):
        assert MatchTolerance.within_tolerance(Decimal("10.00"), Decimal("10.00")) is True

    def test_within_tolerance_at_boundary(self):
        # 0.1% of 10.00 = 0.01 — within relative tolerance
        assert MatchTolerance.within_tolerance(Decimal("10.00"), Decimal("10.01")) is True

    def test_outside_tolerance(self):
        # Diff is 5.00, exceeds both 1.00 absolute and 0.1% relative (0.01)
        assert MatchTolerance.within_tolerance(Decimal("10.00"), Decimal("15.00")) is False
        assert MatchTolerance.within_tolerance(Decimal("10.00"), Decimal("100.00")) is False

    def test_zero_reference_uses_absolute(self):
        # When reference is 0, fall back to absolute tolerance (¥1.00)
        assert MatchTolerance.within_tolerance(Decimal("0"), Decimal("0.99")) is True
        assert MatchTolerance.within_tolerance(Decimal("0"), Decimal("1.01")) is False


class TestThreeWayMatchHappyPath:
    def test_all_three_sides_match(self):
        result = match_po_gr_invoice(
            po_lines=[_po(1, qty=10, price=Decimal("10.00"))],
            gr_lines=[_gr(1, qty=10)],
            invoice_lines=[_inv(1, qty=10, price=Decimal("10.00"), amount=Decimal("100"))],
        )
        assert result.status == MatchStatus.MATCHED
        assert result.invoice_total == Decimal("100")
        assert result.po_total == Decimal("100")
        assert result.gr_total == Decimal("100")
        assert result.discrepancies == []
        assert "agree" in result.notes.lower()

    def test_multiple_lines_all_match(self):
        result = match_po_gr_invoice(
            po_lines=[_po(1, qty=5, price=Decimal("20")), _po(2, qty=3, price=Decimal("50"))],
            gr_lines=[_gr(1, qty=5), _gr(2, qty=3)],
            invoice_lines=[
                _inv(1, qty=5, price=Decimal("20"), amount=Decimal("100")),
                _inv(2, qty=3, price=Decimal("50"), amount=Decimal("150")),
            ],
        )
        assert result.status == MatchStatus.MATCHED
        assert result.invoice_total == Decimal("250")


class TestThreeWayMatchQtyMismatch:
    def test_invoice_qty_exceeds_gr_qty(self):
        result = match_po_gr_invoice(
            po_lines=[_po(1, qty=10, price=Decimal("10"))],
            gr_lines=[_gr(1, qty=10)],
            invoice_lines=[_inv(1, qty=15, price=Decimal("10"), amount=Decimal("150"))],
        )
        assert result.status == MatchStatus.QTY_MISMATCH
        assert len(result.discrepancies) == 1
        disc = result.discrepancies[0]
        assert disc.discrepancy_type == "qty"
        assert disc.expected == Decimal(10)
        assert disc.actual == Decimal(15)
        assert disc.variance == Decimal(5)

    def test_invoice_qty_less_than_gr_qty(self):
        result = match_po_gr_invoice(
            po_lines=[_po(1, qty=10, price=Decimal("10"))],
            gr_lines=[_gr(1, qty=10)],
            invoice_lines=[_inv(1, qty=7, price=Decimal("10"), amount=Decimal("70"))],
        )
        assert result.status == MatchStatus.QTY_MISMATCH
        assert result.discrepancies[0].variance == Decimal(-3)


class TestThreeWayMatchPriceMismatch:
    def test_invoice_price_exceeds_tolerance(self):
        # 20% above PO price — diff 2.00, exceeds both 1.00 absolute
        # and 0.1% (0.02) relative
        result = match_po_gr_invoice(
            po_lines=[_po(1, qty=10, price=Decimal("10.00"))],
            gr_lines=[_gr(1, qty=10)],
            invoice_lines=[_inv(1, qty=10, price=Decimal("12.00"), amount=Decimal("120"))],
        )
        assert result.status == MatchStatus.PRICE_MISMATCH
        assert result.discrepancies[0].discrepancy_type == "price"
        assert result.discrepancies[0].variance == Decimal("2.00")

    def test_price_within_tolerance_accepted(self):
        # 0.05% difference: well within 0.1% tolerance
        result = match_po_gr_invoice(
            po_lines=[_po(1, qty=10, price=Decimal("10.00"))],
            gr_lines=[_gr(1, qty=10)],
            invoice_lines=[_inv(1, qty=10, price=Decimal("10.005"), amount=Decimal("100.05"))],
        )
        assert result.status == MatchStatus.MATCHED


class TestThreeWayMatchBothMismatch:
    def test_both_qty_and_price_wrong(self):
        # 20% qty over + 20% price over → BOTH_MISMATCH
        result = match_po_gr_invoice(
            po_lines=[_po(1, qty=10, price=Decimal("10"))],
            gr_lines=[_gr(1, qty=10)],
            invoice_lines=[_inv(1, qty=12, price=Decimal("12"), amount=Decimal("144"))],
        )
        assert result.status == MatchStatus.BOTH_MISMATCH
        # Two discrepancies: one for qty, one for price
        assert len(result.discrepancies) == 2
        types = {d.discrepancy_type for d in result.discrepancies}
        assert "qty" in types
        assert "price" in types


class TestThreeWayMatchEdgeCases:
    def test_invoice_with_product_not_in_po(self):
        # Invoice line for product 99, but PO only has product 1
        result = match_po_gr_invoice(
            po_lines=[_po(1, qty=10, price=Decimal("10"))],
            gr_lines=[_gr(1, qty=10)],
            invoice_lines=[_inv(99, qty=5, price=Decimal("10"), amount=Decimal("50"))],
        )
        # Qty matches GR (both 5 and 10 wait — invoice qty 5 vs GR qty 10
        # → qty mismatch), and price mismatches (PO is None)
        assert result.status == MatchStatus.BOTH_MISMATCH
        types = {d.discrepancy_type for d in result.discrepancies}
        assert "qty" in types
        assert "price" in types
        price_disc = next(d for d in result.discrepancies if d.discrepancy_type == "price")
        assert price_disc.expected == Decimal("0")

    def test_invoice_with_product_not_in_gr(self):
        # Invoice for product 1, but GR has no record
        result = match_po_gr_invoice(
            po_lines=[_po(1, qty=10, price=Decimal("10"))],
            gr_lines=[],  # no GR yet
            invoice_lines=[_inv(1, qty=10, price=Decimal("10"), amount=Decimal("100"))],
        )
        assert result.status == MatchStatus.MISSING_GR
        assert "goods receipt" in result.notes.lower()

    def test_invoice_with_no_po(self):
        result = match_po_gr_invoice(
            po_lines=[],
            gr_lines=[_gr(1, qty=10)],
            invoice_lines=[_inv(1, qty=10, price=Decimal("10"), amount=Decimal("100"))],
        )
        assert result.status == MatchStatus.MISSING_PO

    def test_invoice_with_no_po_and_no_gr(self):
        result = match_po_gr_invoice(
            po_lines=[],
            gr_lines=[],
            invoice_lines=[_inv(1, qty=10, price=Decimal("10"), amount=Decimal("100"))],
        )
        # Missing PO is checked first
        assert result.status == MatchStatus.MISSING_PO

    def test_existing_invoice_against_same_po(self):
        # Duplicate guard: PO already has a matched invoice
        result = match_po_gr_invoice(
            po_lines=[_po(1, qty=10, price=Decimal("10"))],
            gr_lines=[_gr(1, qty=10)],
            invoice_lines=[_inv(1, qty=10, price=Decimal("10"), amount=Decimal("100"))],
            existing_matches=1,
        )
        assert result.status == MatchStatus.DUPLICATE
        assert "1 matched" in result.notes

    def test_empty_invoice_is_processed(self):
        # Edge case: invoice with no lines still gets a result
        result = match_po_gr_invoice(
            po_lines=[_po(1, qty=10, price=Decimal("10"))],
            gr_lines=[_gr(1, qty=10)],
            invoice_lines=[],
        )
        # No discrepancies, totals all zero, status MATCHED
        assert result.status == MatchStatus.MATCHED
        assert result.invoice_total == Decimal("0")
        assert result.discrepancies == []


class TestThreeWayMatchResultTotals:
    def test_totals_are_always_computed(self):
        result = match_po_gr_invoice(
            po_lines=[_po(1, qty=10, price=Decimal("10"))],
            gr_lines=[_gr(1, qty=10, cost=Decimal("9"))],  # cost != price
            invoice_lines=[_inv(1, qty=10, price=Decimal("10"), amount=Decimal("100"))],
        )
        # Even when status is MATCHED, all three totals are populated
        assert result.po_total == Decimal("100")  # 10 * 10
        assert result.gr_total == Decimal("90")   # 10 * 9 (cost, not price)
        assert result.invoice_total == Decimal("100")
