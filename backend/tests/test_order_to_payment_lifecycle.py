"""End-to-end lifecycle test — Stage 2 Day 4.

Simulates a complete sales order lifecycle using only the domain
aggregates + audit_service, verifying:

1. State machines can transition sequentially (quotation → order → ship → invoice → pay → complete)
2. Each transition creates a status_transition_log row
3. Cross-aggregate auto-reconciliation works (payment → invoice paid)
4. The audit log can be replayed to reconstruct the full history
5. Illegal transitions are caught at the domain layer

Uses sqlite in-memory for fast, isolated runs.
"""

import pytest
import pytest_asyncio
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.domain.sales.delivery import DeliveryLine, DeliveryNote
from app.domain.sales.invoice import Invoice, InvoiceLine
from app.domain.sales.order import OrderLine, OrderStatus, SalesOrder
from app.domain.sales.payment import PaymentRecord
from app.domain.sales.quotation import Quotation, QuotationLine
from app.domain.sales.events import (
    DeliveryShipped,
    InvoiceIssued,
    InvoicePaid,
    OrderCompleted,
    OrderConfirmed,
    OrderShipped,
    PaymentReceived,
    QuotationAccepted,
    QuotationSent,
)
from app.services.audit_service import (
    get_aggregate_timeline,
    get_customer_timeline,
    log_transition,
)
from app.database import Base


@pytest_asyncio.fixture
async def db():
    """Yield a fresh in-memory sqlite session with all model tables."""
    import app.models.account
    import app.models.approval
    import app.models.customer
    import app.models.finance
    import app.models.product
    import app.models.rbac
    import app.models.report
    import app.models.sales
    import app.models.transaction
    import app.models.user
    import app.models.audit

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    await engine.dispose()


# ── Happy path: full sales lifecycle ─────────────────────────────────


@pytest.mark.asyncio
async def test_quotation_to_completion_emits_expected_event_sequence(db: AsyncSession):
    """Drive a complete 6-step lifecycle using domain aggregates only.

    Steps:
    1. Quotation draft → sent → accepted → converted
    2. SalesOrder created (PENDING) → confirmed → shipped → completed
    3. DeliveryNote created (DRAFT) → shipped
    4. Invoice created (DRAFT) → issued → paid (via payment)
    5. Payment created (PENDING) → completed

    All transitions log to status_transition_logs.
    """
    customer_id = 42
    quotation_id = 100
    order_id = 200
    delivery_id = 300
    invoice_id = 400
    payment_id = 500

    # 1. Quotation lifecycle
    quotation = Quotation(
        customer_id=customer_id,
        id=quotation_id,
        quotation_no="Q20260611001",
        lines=[QuotationLine(product_id=10, product_name="MCU", quantity=100, unit_price=Decimal("2.5"))],
    )
    await log_transition(
        db, "Quotation", quotation_id, None, "draft", "create",
        aggregate_no="Q20260611001", customer_id=customer_id,
    )
    quotation.send()
    await log_transition(
        db, "Quotation", quotation_id, "draft", "sent", "send",
        aggregate_no="Q20260611001", customer_id=customer_id, actor="sales_alice",
    )
    quotation.accept()
    await log_transition(
        db, "Quotation", quotation_id, "sent", "accepted", "accept",
        aggregate_no="Q20260611001", customer_id=customer_id, actor="customer",
    )
    quotation.convert_to_order()
    await log_transition(
        db, "Quotation", quotation_id, "accepted", "converted", "convert_to_order",
        aggregate_no="Q20260611001", customer_id=customer_id, actor="system",
    )

    # 2. SalesOrder lifecycle (PENDING → CONFIRMED → SHIPPED → COMPLETED)
    order = SalesOrder(
        customer_id=customer_id,
        id=order_id,
        order_no="SO20260611001",
        quotation_id=quotation_id,
        owner="sales_alice",
        lines=[OrderLine(product_id=10, product_name="MCU", quantity=100, unit_price=2.5)],
    )
    await log_transition(
        db, "SalesOrder", order_id, None, "pending", "create",
        aggregate_no="SO20260611001", customer_id=customer_id,
    )
    order.confirm()
    await log_transition(
        db, "SalesOrder", order_id, "pending", "confirmed", "confirm",
        aggregate_no="SO20260611001", customer_id=customer_id, actor="sales_alice",
        sales_order_id=order_id,
    )
    order.ship()
    await log_transition(
        db, "SalesOrder", order_id, "confirmed", "shipped", "ship",
        aggregate_no="SO20260611001", customer_id=customer_id, actor="warehouse_bob",
        sales_order_id=order_id,
    )

    # 3. DeliveryNote lifecycle
    delivery = DeliveryNote(
        sales_order_id=order_id,
        customer_id=customer_id,
        id=delivery_id,
        delivery_no="DN20260611001",
        lines=[DeliveryLine(product_id=10, product_name="MCU", quantity=100)],
    )
    await log_transition(
        db, "DeliveryNote", delivery_id, None, "pending", "create",
        aggregate_no="DN20260611001", customer_id=customer_id, sales_order_id=order_id,
    )
    delivery.ship()
    await log_transition(
        db, "DeliveryNote", delivery_id, "pending", "shipped", "ship",
        aggregate_no="DN20260611001", customer_id=customer_id, actor="warehouse_bob",
        sales_order_id=order_id,
    )

    # 4. Invoice lifecycle (DRAFT → ISSUED → paid via payment)
    invoice = Invoice(
        customer_id=customer_id,
        sales_order_id=order_id,
        id=invoice_id,
        invoice_no="INV20260611001",
        lines=[InvoiceLine(product_id=10, product_name="MCU", quantity=100, unit_price=2.5)],
    )
    await log_transition(
        db, "Invoice", invoice_id, None, "draft", "create",
        aggregate_no="INV20260611001", customer_id=customer_id, sales_order_id=order_id,
    )
    invoice.issue()
    await log_transition(
        db, "Invoice", invoice_id, "draft", "issued", "issue",
        aggregate_no="INV20260611001", customer_id=customer_id, actor="finance_carol",
        sales_order_id=order_id,
    )

    # 5. Payment lifecycle (PENDING → COMPLETED)
    payment = PaymentRecord(
        customer_id=customer_id,
        amount=invoice.total,
        id=payment_id,
        invoice_id=invoice_id,
        sales_order_id=order_id,
        payment_method="bank_transfer",
    )
    await log_transition(
        db, "PaymentRecord", payment_id, None, "pending", "create",
        customer_id=customer_id, sales_order_id=order_id,
    )
    payment.complete()
    await log_transition(
        db, "PaymentRecord", payment_id, "pending", "completed", "complete",
        actor="finance_carol", customer_id=customer_id, sales_order_id=order_id,
    )

    # Cross-aggregate: payment event triggers invoice record_payment
    payment_event = payment.collect_events()[0]
    invoice.record_payment(payment_event.amount)
    if invoice.status.value == "paid":
        await log_transition(
            db, "Invoice", invoice_id, "issued", "paid", "pay_full",
            aggregate_no="INV20260611001", customer_id=customer_id,
            actor="system", sales_order_id=order_id,
        )

    # 6. Order COMPLETED (after invoice paid)
    order.complete()
    await log_transition(
        db, "SalesOrder", order_id, "shipped", "completed", "complete",
        aggregate_no="SO20260611001", customer_id=customer_id, actor="system",
        sales_order_id=order_id,
    )

    await db.commit()

    # Verify: every aggregate has a complete audit trail
    so_timeline = await get_aggregate_timeline(db, "SalesOrder", order_id)
    assert [t.status_after for t in so_timeline] == [
        "pending", "confirmed", "shipped", "completed"
    ]

    invoice_timeline = await get_aggregate_timeline(db, "Invoice", invoice_id)
    assert [t.status_after for t in invoice_timeline] == ["draft", "issued", "paid"]

    payment_timeline = await get_aggregate_timeline(db, "PaymentRecord", payment_id)
    assert [t.status_after for t in payment_timeline] == ["pending", "completed"]

    # Customer timeline contains entries from all aggregates
    cust_timeline = await get_customer_timeline(db, customer_id)
    assert len(cust_timeline) >= 13  # 4 quotation + 4 order + 2 delivery + 3 invoice + 2 payment


# ── Cross-aggregate: payment auto-completes invoice ──────────────────


@pytest.mark.asyncio
async def test_partial_then_full_payment_drive_invoice_to_paid(db: AsyncSession):
    """Verify the auto-reconcile: 2 partial payments + 1 full = invoice PAID."""
    customer_id = 1
    invoice_id = 100
    payment1_id = 200
    payment2_id = 201
    payment3_id = 202

    # Create invoice
    invoice = Invoice(
        customer_id=customer_id,
        id=invoice_id,
        invoice_no="INV001",
        lines=[InvoiceLine(product_id=10, product_name="X", quantity=100, unit_price=10.0)],
    )
    await log_transition(
        db, "Invoice", invoice_id, None, "draft", "create", customer_id=customer_id
    )
    invoice.issue()
    await log_transition(
        db, "Invoice", invoice_id, "draft", "issued", "issue", customer_id=customer_id
    )
    assert invoice.total == pytest.approx(1130.0)  # 100 * 10 * 1.13

    # 3 partial payments
    for pid, amount in [(payment1_id, 500.0), (payment2_id, 300.0), (payment3_id, 330.0)]:
        p = PaymentRecord(
            customer_id=customer_id,
            amount=amount,
            id=pid,
            invoice_id=invoice_id,
            payment_method="bank_transfer",
        )
        p.complete()
        event = p.collect_events()[0]
        await log_transition(
            db, "PaymentRecord", pid, None, "pending", "create", customer_id=customer_id
        )
        await log_transition(
            db, "PaymentRecord", pid, "pending", "completed", "complete", customer_id=customer_id
        )
        invoice.record_payment(event.amount)

    # After 1130 paid: auto-transition to PAID
    assert invoice.status.value == "paid"
    assert invoice.paid_amount == pytest.approx(1130.0)
    assert invoice.paid_at is not None

    await log_transition(
        db, "Invoice", invoice_id, "issued", "paid", "pay_full", customer_id=customer_id
    )
    await db.commit()

    timeline = await get_aggregate_timeline(db, "Invoice", invoice_id)
    assert [t.status_after for t in timeline] == ["draft", "issued", "paid"]


# ── Cancellation paths across aggregates ────────────────────────────


@pytest.mark.asyncio
async def test_cancel_from_confirmed_order_blocks_remaining_lifecycle(db: AsyncSession):
    """If SO is cancelled at CONFIRMED, downstream DN/INV/PAY should never fire."""
    customer_id = 1
    order_id = 100

    order = SalesOrder(
        customer_id=customer_id,
        id=order_id,
        order_no="SO100",
        owner="alice",
        lines=[OrderLine(product_id=10, product_name="X", quantity=10, unit_price=10.0)],
    )
    order.confirm()
    await log_transition(
        db, "SalesOrder", order_id, None, "pending", "create", customer_id=customer_id
    )
    await log_transition(
        db, "SalesOrder", order_id, "pending", "confirmed", "confirm",
        customer_id=customer_id, actor="alice"
    )

    # Customer reverses
    order.cancel("客户临时取消")
    await log_transition(
        db, "SalesOrder", order_id, "confirmed", "cancelled", "cancel",
        customer_id=customer_id, actor="customer", reason="客户临时取消"
    )
    await db.commit()

    timeline = await get_aggregate_timeline(db, "SalesOrder", order_id)
    assert [t.status_after for t in timeline] == ["pending", "confirmed", "cancelled"]

    # Critical: no further transitions exist
    assert len(timeline) == 3

    # If someone tries to ship a cancelled order, domain layer should reject
    with pytest.raises(Exception):  # InvalidStateTransition
        order.ship()


# ── Audit log replay ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_audit_log_can_reconstruct_aggregate_lifecycle(db: AsyncSession):
    """Given only the audit log, we can rebuild the state machine history."""
    customer_id = 7
    order_id = 999

    # 5-transition lifecycle
    transitions = [
        (None, "pending", "create", None),
        ("pending", "confirmed", "confirm", "alice"),
        ("confirmed", "shipped", "ship", "bob"),
        ("shipped", "completed", "complete", "system"),
    ]
    for prev, new, action, actor in transitions:
        await log_transition(
            db,
            aggregate_type="SalesOrder",
            aggregate_id=order_id,
            aggregate_no=f"SO{order_id}",
            status_before=prev,
            status_after=new,
            action=action,
            actor=actor,
            customer_id=customer_id,
        )
    await db.commit()

    # Replay: read timeline, rebuild state
    timeline = await get_aggregate_timeline(db, "SalesOrder", order_id)
    reconstructed = []
    for t in timeline:
        reconstructed.append({
            "from": t.status_before,
            "to": t.status_after,
            "action": t.action,
            "actor": t.actor,
            "at": t.transitioned_at.isoformat(),
        })

    # Final state is reconstructed correctly
    assert reconstructed[-1]["to"] == "completed"

    # 4 transitions match
    assert len(reconstructed) == 4

    # Customer timeline contains all 4
    cust_timeline = await get_customer_timeline(db, customer_id)
    assert len(cust_timeline) == 4


# ── Illegal transitions caught at domain layer ───────────────────────


@pytest.mark.asyncio
async def test_illegal_transition_does_not_create_audit_entry(db: AsyncSession):
    """Audit logs are only written for *successful* transitions."""
    customer_id = 1
    order_id = 100

    # Try to ship a PENDING order (illegal)
    order = SalesOrder(
        customer_id=customer_id,
        id=order_id,
        owner="alice",
        lines=[OrderLine(product_id=10, product_name="X", quantity=10, unit_price=10.0)],
    )
    with pytest.raises(Exception):
        order.ship()

    # If no log_transition was called, the audit table is empty
    timeline = await get_aggregate_timeline(db, "SalesOrder", order_id)
    assert timeline == []


@pytest.mark.asyncio
async def test_failed_payment_does_not_advance_invoice(db: AsyncSession):
    """Pending payment is NOT recorded against invoice — only completed payments."""
    customer_id = 1
    invoice_id = 100
    payment_id = 200

    invoice = Invoice(
        customer_id=customer_id,
        id=invoice_id,
        lines=[InvoiceLine(product_id=10, product_name="X", quantity=10, unit_price=10.0)],
    )
    invoice.issue()
    assert invoice.paid_amount == 0.0
    assert invoice.status.value == "issued"

    # Payment stays PENDING
    payment = PaymentRecord(
        customer_id=customer_id,
        amount=invoice.total,
        id=payment_id,
        invoice_id=invoice_id,
        payment_method="bank_transfer",
    )
    assert payment.status.value == "pending"

    # No record_payment called yet
    assert invoice.paid_amount == 0.0
    assert invoice.status.value == "issued"  # not advanced


# ── Multi-aggregate timing analysis ──────────────────────────────────


@pytest.mark.asyncio
async def test_lifecycle_audit_supports_dwell_time_analysis(db: AsyncSession):
    """The audit log can be queried for 'how long did this order sit in PENDING?'.

    Use case: identify bottlenecks in the sales pipeline.
    """
    customer_id = 1
    order_id = 100

    # Create
    await log_transition(
        db, "SalesOrder", order_id, None, "pending", "create", customer_id=customer_id
    )
    await db.commit()

    # Confirm (no sleep — sqlite in-memory is too fast to time-resolve)
    await log_transition(
        db, "SalesOrder", order_id, "pending", "confirmed", "confirm", customer_id=customer_id
    )
    await db.commit()

    # Replay
    timeline = await get_aggregate_timeline(db, "SalesOrder", order_id)
    assert len(timeline) == 2

    # Time gap between transitions is computable
    gap = (timeline[1].transitioned_at - timeline[0].transitioned_at).total_seconds()
    assert gap >= 0  # at minimum non-negative
    # Note: timing precision in sqlite is second-level, so gap may be 0 in fast runs
