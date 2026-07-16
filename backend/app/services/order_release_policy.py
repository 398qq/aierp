"""Operational release controls applied before an order can be delivered."""

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer import Customer
from app.models.finance import Contract, Invoice, PaymentAllocation
from app.models.sales import SalesOrder


async def validate_order_release(db: AsyncSession, order: SalesOrder) -> str | None:
    customer = await db.get(Customer, order.customer_id)
    if customer is None:
        return "订单客户不存在"

    if customer.contract_required:
        signed_contracts = int(
            await db.scalar(
                select(func.count(Contract.id)).where(
                    Contract.sales_order_id == order.id,
                    Contract.deleted_at.is_(None),
                    Contract.status.in_(["signed", "active", "effective"]),
                )
            )
            or 0
        )
        if signed_contracts == 0:
            return "该客户要求先签合同，当前订单没有已签署合同"

    if not customer.credit_control_enabled:
        return None

    invoices = list(
        (
            await db.scalars(
                select(Invoice).where(
                    Invoice.customer_id == customer.id,
                    Invoice.deleted_at.is_(None),
                    Invoice.status.notin_(["paid", "cancelled"]),
                )
            )
        ).all()
    )
    outstanding = 0.0
    overdue = False
    now = datetime.now(timezone.utc)
    for invoice in invoices:
        allocated = float(
            await db.scalar(
                select(func.coalesce(func.sum(PaymentAllocation.amount), 0)).where(
                    PaymentAllocation.invoice_id == invoice.id,
                    PaymentAllocation.deleted_at.is_(None),
                )
            )
            or 0
        )
        balance = max(float(invoice.amount or 0) - allocated, 0)
        outstanding += balance
        if balance > 0 and invoice.due_date and invoice.due_date < now:
            overdue = True

    if overdue:
        return "客户存在逾期未核销发票，订单已被信用控制拦截"
    credit_limit = float(customer.credit_limit or 0)
    if credit_limit > 0 and outstanding + float(order.total_amount or 0) > credit_limit:
        return "客户应收余额加本订单金额已超过信用额度"
    return None
