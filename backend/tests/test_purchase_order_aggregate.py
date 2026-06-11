"""Tests for PurchaseOrder aggregate."""

import pytest

from app.domain.procurement.entities import (
    POStatus,
    PurchaseOrder,
    PurchaseOrderLine,
)
from app.domain.procurement.events import (
    GoodsReceived,
    PurchaseOrderApproved,
    PurchaseOrderCancelled,
)
from app.domain.shared.errors import (
    BusinessRuleViolation,
    InvalidStateTransition,
)


def _line(product_id: int = 1, qty: int = 10, price: float = 50.0) -> PurchaseOrderLine:
    return PurchaseOrderLine(
        product_id=product_id,
        product_name=f"Product {product_id}",
        quantity=qty,
        unit_price=price,
    )


class TestPurchaseOrderLine:
    def test_amount(self):
        line = _line(qty=3, price=12.5)
        assert line.amount == 37.5

    def test_rejects_zero_quantity(self):
        with pytest.raises(BusinessRuleViolation):
            _line(qty=0)

    def test_rejects_negative_price(self):
        with pytest.raises(BusinessRuleViolation):
            _line(price=-1.0)


class TestPurchaseOrderBasics:
    def test_total(self):
        po = PurchaseOrder(
            supplier_id=1,
            lines=[_line(qty=2, price=100), _line(qty=3, price=50)],
        )
        assert po.total == 350.0

    def test_add_line_in_draft(self):
        po = PurchaseOrder(supplier_id=1)
        po.add_line(_line())
        assert len(po.lines) == 1

    def test_add_line_after_approve_raises(self):
        po = PurchaseOrder(supplier_id=1, lines=[_line()])
        po.approve()
        with pytest.raises(InvalidStateTransition):
            po.add_line(_line())


class TestPurchaseOrderApprove:
    def test_approve_draft(self):
        po = PurchaseOrder(supplier_id=1, lines=[_line()])
        po.approve()
        assert po.status == POStatus.APPROVED

    def test_approve_emits_event(self):
        po = PurchaseOrder(
            supplier_id=42,
            order_no="PO-001",
            lines=[_line()],
        )
        po.approve()
        events = po.collect_events()
        assert len(events) == 1
        assert isinstance(events[0], PurchaseOrderApproved)
        assert events[0].supplier_id == 42
        assert events[0].order_no == "PO-001"

    def test_approve_empty_raises(self):
        po = PurchaseOrder(supplier_id=1, lines=[])
        with pytest.raises(BusinessRuleViolation, match="空采购单"):
            po.approve()

    def test_approve_already_approved_raises(self):
        po = PurchaseOrder(supplier_id=1, lines=[_line()])
        po.approve()
        with pytest.raises(InvalidStateTransition):
            po.approve()


class TestPurchaseOrderOrdered:
    def test_mark_ordered_from_approved(self):
        po = PurchaseOrder(supplier_id=1, lines=[_line()])
        po.approve()
        po.mark_ordered()
        assert po.status == POStatus.ORDERED

    def test_mark_ordered_from_draft_raises(self):
        po = PurchaseOrder(supplier_id=1, lines=[_line()])
        with pytest.raises(InvalidStateTransition):
            po.mark_ordered()


class TestPurchaseOrderReceive:
    def test_receive_goods_from_ordered(self):
        po = PurchaseOrder(supplier_id=1, lines=[_line(product_id=1, qty=10)])
        po.approve()
        po.mark_ordered()
        po.receive_goods([(1, 5)])
        assert po.status == POStatus.PARTIALLY_RECEIVED

    def test_receive_goods_emits_event(self):
        po = PurchaseOrder(
            supplier_id=42,
            lines=[_line(product_id=1, qty=10), _line(product_id=2, qty=5)],
        )
        po.approve()
        po.mark_ordered()
        po.receive_goods([(1, 5), (2, 5)])
        events = po.collect_events()
        gr_events = [e for e in events if isinstance(e, GoodsReceived)]
        assert len(gr_events) == 1
        assert gr_events[0].receipts == ((1, 5), (2, 5))

    def test_receive_unknown_product_raises(self):
        po = PurchaseOrder(
            supplier_id=1,
            lines=[_line(product_id=1, qty=10)],
        )
        po.approve()
        po.mark_ordered()
        with pytest.raises(BusinessRuleViolation, match="不包含产品"):
            po.receive_goods([(999, 5)])

    def test_receive_zero_qty_raises(self):
        po = PurchaseOrder(
            supplier_id=1,
            lines=[_line(product_id=1, qty=10)],
        )
        po.approve()
        po.mark_ordered()
        with pytest.raises(BusinessRuleViolation):
            po.receive_goods([(1, 0)])

    def test_receive_from_draft_raises(self):
        po = PurchaseOrder(
            supplier_id=1,
            lines=[_line(product_id=1, qty=10)],
        )
        with pytest.raises(InvalidStateTransition):
            po.receive_goods([(1, 5)])


class TestPurchaseOrderCancel:
    def test_cancel_from_draft(self):
        po = PurchaseOrder(supplier_id=1, lines=[_line()])
        po.cancel(reason="supplier out of stock")
        assert po.status == POStatus.CANCELLED

    def test_cancel_from_approved_emits_event(self):
        po = PurchaseOrder(
            supplier_id=1,
            lines=[_line()],
        )
        po.approve()
        po.cancel(reason="changed mind")
        events = po.collect_events()
        cancel_events = [e for e in events if isinstance(e, PurchaseOrderCancelled)]
        assert len(cancel_events) == 1
        assert cancel_events[0].previous_status == "approved"
        assert cancel_events[0].reason == "changed mind"

    def test_cancel_from_received_raises(self):
        po = PurchaseOrder(
            supplier_id=1,
            lines=[_line(product_id=1, qty=10)],
        )
        po.approve()
        po.mark_ordered()
        po.receive_goods([(1, 10)])
        po.mark_fully_received()
        with pytest.raises(InvalidStateTransition):
            po.cancel(reason="too late")
