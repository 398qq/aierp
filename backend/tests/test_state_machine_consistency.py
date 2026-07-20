"""Cross-layer contracts for canonical ERP lifecycle vocabularies."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from httpx import AsyncClient
from pydantic import ValidationError

from app.domain.sales.delivery import DeliveryLine, DeliveryNote, DeliveryStatus
from app.domain.sales.payment import PaymentRecord, PaymentStatus
from app.domain.sales.quotation import Quotation, QuotationLine, QuotationStatus
from app.domain.states import (
    assert_can_transition_delivery,
    assert_can_transition_payment,
    assert_can_transition_quotation,
)


def test_quotation_aggregate_uses_canonical_won_status() -> None:
    quote = Quotation(
        customer_id=1,
        lines=[
            QuotationLine(
                product_id=1,
                product_name="测试产品",
                quantity=1,
                unit_price=Decimal("100"),
            )
        ],
    )
    quote.send()
    quote.convert_to_order()

    assert quote.status is QuotationStatus.WON
    assert_can_transition_quotation("sent", quote.status.value)


def test_delivery_aggregate_uses_canonical_delivered_status() -> None:
    note = DeliveryNote(
        sales_order_id=1,
        customer_id=1,
        lines=[DeliveryLine(product_id=1, product_name="测试产品", quantity=1)],
    )
    note.ship()
    note.confirm_receipt()

    assert note.status is DeliveryStatus.DELIVERED
    assert_can_transition_delivery("shipped", note.status.value)


def test_payment_reversal_is_part_of_canonical_state_machine() -> None:
    payment = PaymentRecord(customer_id=1, amount=100)
    payment.complete()
    payment.reverse("退款")

    assert payment.status is PaymentStatus.REVERSED
    assert_can_transition_payment("completed", payment.status.value)


def test_partial_payment_can_later_be_completed() -> None:
    assert_can_transition_payment("pending", "partial")
    assert_can_transition_payment("partial", "completed")


async def test_dashboard_counts_canonical_issued_invoice_as_outstanding(
    async_client: AsyncClient,
    auth_headers: dict,
    db_session,
    test_customer: dict,
) -> None:
    from app.models.finance import Invoice
    from app.models.sales import SalesOrder

    order = SalesOrder(customer_id=test_customer["id"], total_amount=321)
    db_session.add(order)
    await db_session.flush()
    db_session.add(
        Invoice(
            sales_order_id=order.id,
            customer_id=test_customer["id"],
            amount=321,
            status="issued",
        )
    )
    await db_session.flush()

    response = await async_client.get("/api/v1/dashboard/kpi", headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["data"]["outstanding_ar"] == 321


async def test_po_calendar_includes_canonical_ordered_purchase_order(
    async_client: AsyncClient,
    admin_headers: dict,
    db_session,
) -> None:
    from app.models.product import Supplier
    from app.models.transaction import PurchaseOrder

    supplier = Supplier(name="测试供应商")
    db_session.add(supplier)
    await db_session.flush()
    po = PurchaseOrder(
        supplier_id=supplier.id,
        order_no="PO-CANONICAL",
        status="ordered",
        expected_date=datetime.now(timezone.utc) + timedelta(days=3),
    )
    db_session.add(po)
    await db_session.flush()

    response = await async_client.get(
        "/api/v1/ai/procurement/po-calendar", headers=admin_headers
    )

    assert response.status_code == 200
    assert [item["id"] for item in response.json()["data"]] == [po.id]


async def test_sample_create_rejects_noncanonical_initial_status(
    async_client: AsyncClient,
    auth_headers: dict,
    test_customer: dict,
) -> None:
    response = await async_client.post(
        "/api/v1/samples",
        headers=auth_headers,
        json={"customer_id": test_customer["id"], "status": "requested"},
    )

    assert response.status_code == 422


def test_core_document_create_schemas_reject_terminal_initial_statuses() -> None:
    from app.schemas.finance import InvoiceCreate, PaymentRecordCreate
    from app.schemas.sales import DeliveryNoteCreate, QuotationCreate, SalesOrderCreate

    invalid_payloads = [
        (QuotationCreate, {"customer_id": 1, "status": "won"}),
        (SalesOrderCreate, {"customer_id": 1, "status": "completed"}),
        (
            DeliveryNoteCreate,
            {"sales_order_id": 1, "customer_id": 1, "status": "delivered"},
        ),
        (
            InvoiceCreate,
            {
                "sales_order_id": 1,
                "customer_id": 1,
                "amount": 1,
                "status": "paid",
            },
        ),
        (
            PaymentRecordCreate,
            {"customer_id": 1, "amount": 1, "status": "completed"},
        ),
    ]

    for schema, payload in invalid_payloads:
        try:
            schema.model_validate(payload)
        except ValidationError:
            continue
        raise AssertionError(f"{schema.__name__} accepted illegal initial status")


def test_core_document_update_schemas_reject_unknown_statuses() -> None:
    from app.schemas.finance import InvoiceUpdate, PaymentRecordUpdate
    from app.schemas.sales import DeliveryNoteUpdate, QuotationUpdate, SalesOrderUpdate

    for schema in (
        QuotationUpdate,
        SalesOrderUpdate,
        DeliveryNoteUpdate,
        InvoiceUpdate,
        PaymentRecordUpdate,
    ):
        try:
            schema.model_validate({"status": "not-a-real-status"})
        except ValidationError:
            continue
        raise AssertionError(f"{schema.__name__} accepted an unknown status")


async def test_canonical_transition_guard_mutates_and_writes_audit_atomically(
    db_session,
    test_customer: dict,
) -> None:
    from sqlalchemy import select

    from app.domain.states import assert_can_transition_sales_order
    from app.models.audit import StatusTransitionLog
    from app.models.sales import SalesOrder
    from app.services.state_transition_service import transition_status

    order = SalesOrder(
        customer_id=test_customer["id"],
        order_no="SO-AUDIT",
        status="pending",
    )
    db_session.add(order)
    await db_session.flush()

    changed = await transition_status(
        db_session,
        order,
        "confirmed",
        guard=assert_can_transition_sales_order,
        aggregate_type="SalesOrder",
        actor="7",
    )

    audit = await db_session.scalar(
        select(StatusTransitionLog).where(
            StatusTransitionLog.aggregate_type == "SalesOrder",
            StatusTransitionLog.aggregate_id == order.id,
        )
    )
    assert changed is True
    assert order.status == "confirmed"
    assert audit is not None
    assert (audit.status_before, audit.status_after, audit.actor) == (
        "pending",
        "confirmed",
        "7",
    )


async def test_ticket_transition_endpoint_enforces_guard_and_records_actor(
    async_client: AsyncClient,
    auth_headers: dict,
    db_session,
    test_customer: dict,
    test_user: dict,
) -> None:
    from sqlalchemy import select

    from app.models.audit import StatusTransitionLog

    created = await async_client.post(
        "/api/v1/tickets",
        headers=auth_headers,
        json={"customer_id": test_customer["id"], "title": "状态机工单"},
    )
    ticket_id = created.json()["data"]["id"]

    illegal = await async_client.post(
        f"/api/v1/tickets/{ticket_id}/transition",
        headers=auth_headers,
        json={"target_status": "resolved"},
    )
    assert illegal.status_code == 422

    progressed = await async_client.post(
        f"/api/v1/tickets/{ticket_id}/transition",
        headers=auth_headers,
        json={"target_status": "in_progress"},
    )
    assert progressed.status_code == 200
    assert progressed.json()["data"]["status"] == "in_progress"

    audit = await db_session.scalar(
        select(StatusTransitionLog).where(
            StatusTransitionLog.aggregate_type == "Ticket",
            StatusTransitionLog.aggregate_id == ticket_id,
        )
    )
    assert audit is not None
    assert audit.actor == str(test_user["id"])


async def test_sample_transition_endpoint_uses_pending_lifecycle(
    async_client: AsyncClient,
    auth_headers: dict,
    test_customer: dict,
) -> None:
    created = await async_client.post(
        "/api/v1/samples",
        headers=auth_headers,
        json={"customer_id": test_customer["id"]},
    )
    sample_id = created.json()["data"]["id"]

    response = await async_client.post(
        f"/api/v1/samples/{sample_id}/transition",
        headers=auth_headers,
        json={"target_status": "shipped"},
    )

    assert response.status_code == 200
    assert response.json()["data"]["status"] == "shipped"
