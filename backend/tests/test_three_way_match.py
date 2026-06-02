"""Tests for three-way match (PO / GR / Invoice) domain logic."""

from decimal import Decimal


from app.domain.procurement.three_way_match import (
    GRLineSnapshot,
    InvoiceLineSnapshot,
    MatchStatus,
    MatchTolerance,
    POLineSnapshot,
    match_po_gr_invoice,
)


def _po(product_id: int, qty: int = 10, price: str = "100.0") -> POLineSnapshot:
    return POLineSnapshot(
        product_id=product_id, quantity=qty,
        unit_price=Decimal(price),
    )


def _gr(product_id: int, qty: int = 10, cost: str = "100.0") -> GRLineSnapshot:
    return GRLineSnapshot(
        product_id=product_id, quantity_received=qty,
        unit_cost=Decimal(cost),
    )


def _inv(
    product_id: int, qty: int = 10, price: str = "100.0", amount: str = "1000.0"
) -> InvoiceLineSnapshot:
    return InvoiceLineSnapshot(
        product_id=product_id, quantity=qty,
        unit_price=Decimal(price), amount=Decimal(amount),
    )


class TestMatchTolerance:
    def test_exact_match_within_tolerance(self):
        assert MatchTolerance.within_tolerance(Decimal("100"), Decimal("100")) is True

    def test_within_1_yuan_tolerance(self):
        assert MatchTolerance.within_tolerance(
            Decimal("100"), Decimal("100.5")
        ) is True

    def test_within_pct_tolerance(self):
        # 0.05% off
        assert MatchTolerance.within_tolerance(
            Decimal("10000"), Decimal("10005")
        ) is True

    def test_outside_both_tolerances(self):
        # 5% off
        assert MatchTolerance.within_tolerance(
            Decimal("1000"), Decimal("1050")
        ) is False

    def test_pct_uses_actual_not_expected(self):
        # 0.5% off, just outside
        assert MatchTolerance.within_tolerance(
            Decimal("10000"), Decimal("10050")
        ) is False


class TestThreeWayMatchHappyPath:
    def test_perfect_match(self):
        po = [_po(1, 10, "100"), _po(2, 5, "200")]
        gr = [_gr(1, 10, "100"), _gr(2, 5, "200")]
        inv = [_inv(1, 10, "100", "1000"), _inv(2, 5, "200", "1000")]

        result = match_po_gr_invoice(po, gr, inv)

        assert result.status == MatchStatus.MATCHED
        assert result.is_matched is True
        assert result.requires_clerk_review is False
        assert result.discrepancies == []
        assert result.invoice_total == Decimal("2000")

    def test_within_1pct_price_tolerance(self):
        po = [_po(1, 10, "100")]
        gr = [_gr(1, 10, "100")]
        # 0.5% price increase — within tolerance
        inv = [_inv(1, 10, "100.5", "1005")]

        result = match_po_gr_invoice(po, gr, inv)

        assert result.status == MatchStatus.MATCHED
        assert len(result.discrepancies) == 0


class TestThreeWayMatchQtyMismatch:
    def test_invoice_qty_exceeds_gr(self):
        po = [_po(1, 10)]
        gr = [_gr(1, 8)]  # Only 8 received
        inv = [_inv(1, 10, "100", "1000")]

        result = match_po_gr_invoice(po, gr, inv)

        assert result.status == MatchStatus.QTY_MISMATCH
        assert result.requires_clerk_review is True
        assert len(result.discrepancies) == 1
        d = result.discrepancies[0]
        assert d.product_id == 1
        assert d.discrepancy_type == "qty"
        assert d.expected == Decimal("8")
        assert d.actual == Decimal("10")
        assert d.variance == Decimal("2")

    def test_invoice_qty_less_than_gr(self):
        po = [_po(1, 10)]
        gr = [_gr(1, 10)]
        inv = [_inv(1, 8, "100", "800")]  # Under-billed

        result = match_po_gr_invoice(po, gr, inv)

        assert result.status == MatchStatus.QTY_MISMATCH
        d = result.discrepancies[0]
        assert d.variance == Decimal("-2")


class TestThreeWayMatchPriceMismatch:
    def test_invoice_price_too_high(self):
        po = [_po(1, 10, "100")]
        gr = [_gr(1, 10, "100")]
        inv = [_inv(1, 10, "110", "1100")]  # 10% over PO

        result = match_po_gr_invoice(po, gr, inv)

        assert result.status == MatchStatus.PRICE_MISMATCH
        d = result.discrepancies[0]
        assert d.discrepancy_type == "price"
        assert d.variance == Decimal("10")

    def test_invoice_price_too_low(self):
        po = [_po(1, 10, "100")]
        gr = [_gr(1, 10, "100")]
        inv = [_inv(1, 10, "90", "900")]

        result = match_po_gr_invoice(po, gr, inv)

        assert result.status == MatchStatus.PRICE_MISMATCH
        d = result.discrepancies[0]
        assert d.variance == Decimal("-10")


class TestThreeWayMatchBothMismatch:
    def test_both_qty_and_price_off(self):
        po = [_po(1, 10, "100")]
        gr = [_gr(1, 8, "100")]
        inv = [_inv(1, 10, "110", "1100")]

        result = match_po_gr_invoice(po, gr, inv)

        assert result.status == MatchStatus.BOTH_MISMATCH
        assert len(result.discrepancies) == 2
        types = {d.discrepancy_type for d in result.discrepancies}
        assert types == {"qty", "price"}


class TestThreeWayMatchEdgeCases:
    def test_missing_po(self):
        gr = [_gr(1)]
        inv = [_inv(1)]
        result = match_po_gr_invoice([], gr, inv)
        assert result.status == MatchStatus.MISSING_PO
        assert "No matching purchase order" in result.notes

    def test_missing_gr(self):
        po = [_po(1)]
        inv = [_inv(1)]
        result = match_po_gr_invoice(po, [], inv)
        assert result.status == MatchStatus.MISSING_GR
        assert "No goods receipt" in result.notes

    def test_duplicate_invoice(self):
        po = [_po(1)]
        gr = [_gr(1)]
        inv = [_inv(1)]
        result = match_po_gr_invoice(po, gr, inv, existing_matches=1)
        assert result.status == MatchStatus.DUPLICATE
        assert "already has 1 matched" in result.notes

    def test_invoice_line_for_product_not_in_po(self):
        po = [_po(1)]
        gr = [_gr(1), _gr(2)]  # 2 was received
        inv = [_inv(1), _inv(2, price="100", amount="1000")]

        result = match_po_gr_invoice(po, gr, inv)

        # Line 2 has no PO entry → price mismatch
        assert any(
            d.product_id == 2 and d.discrepancy_type == "price"
            for d in result.discrepancies
        )

    def test_totals_calculated_correctly(self):
        po = [_po(1, 10, "100"), _po(2, 5, "200")]
        gr = [_gr(1, 10, "100"), _gr(2, 5, "200")]
        inv = [_inv(1, 10, "100", "1000"), _inv(2, 5, "200", "1000")]

        result = match_po_gr_invoice(po, gr, inv)
        assert result.po_total == Decimal("2000")
        assert result.gr_total == Decimal("2000")
        assert result.invoice_total == Decimal("2000")

    def test_notes_describe_discrepancy_count(self):
        po = [_po(1, 10, "100"), _po(2, 5, "200")]
        gr = [_gr(1, 8, "100"), _gr(2, 5, "200")]
        inv = [_inv(1, 10, "100", "1000"), _inv(2, 5, "200", "1000")]

        result = match_po_gr_invoice(po, gr, inv)
        assert "1 line discrepancies" in result.notes
        assert "total variance" in result.notes

    def test_perfect_match_has_clean_notes(self):
        po = [_po(1)]
        gr = [_gr(1)]
        inv = [_inv(1)]
        result = match_po_gr_invoice(po, gr, inv)
        assert "All three sides agree" in result.notes
