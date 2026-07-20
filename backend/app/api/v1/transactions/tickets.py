"""Transactions API — ticket bounded context.

Customer support / after-sales tickets.
"""

import logging
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.domain.shared.errors import NotFoundError
from app.domain.states import assert_can_transition_ticket
from app.models.transaction import Ticket
from app.schemas.common import ok
from app.services.state_transition_service import transition_status

logger = logging.getLogger(__name__)

ticket_router = APIRouter(prefix="/tickets", tags=["transactions:ticket"])


class TicketCreate(BaseModel):
    ticket_no: str | None = None
    customer_id: int | None = None
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    status: Literal["open"] = "open"
    priority: str = "medium"
    category: str | None = None
    assigned_to: str | None = None
    notes: str | None = None


class TicketTransition(BaseModel):
    target_status: Literal[
        "open", "in_progress", "resolved", "closed", "cancelled"
    ]
    reason: str | None = None


@ticket_router.get("")
async def list_tickets(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = None,
    priority: str | None = None,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    base = select(Ticket).where(Ticket.deleted_at.is_(None))
    count_base = select(func.count(Ticket.id)).where(Ticket.deleted_at.is_(None))

    if status:
        base = base.where(Ticket.status == status)
        count_base = count_base.where(Ticket.status == status)
    if priority:
        base = base.where(Ticket.priority == priority)
        count_base = count_base.where(Ticket.priority == priority)

    total = (await db.execute(count_base)).scalar() or 0
    rows = (
        (
            await db.execute(
                base.order_by(Ticket.id.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        )
        .scalars()
        .all()
    )

    return ok(
        {
            "list": [
                {
                    "id": t.id,
                    "ticket_no": t.ticket_no,
                    "customer_id": t.customer_id,
                    "title": t.title,
                    "description": t.description,
                    "status": t.status,
                    "priority": t.priority,
                    "category": t.category,
                    "assigned_to": t.assigned_to,
                    "resolved_at": str(t.resolved_at) if t.resolved_at else None,
                    "notes": t.notes,
                    "created_at": str(t.created_at) if t.created_at else None,
                }
                for t in rows
            ],
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    )


@ticket_router.post("", status_code=201)
async def create_ticket(
    body: TicketCreate,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    data = body.model_dump()
    if data.get("customer_id") is None:
        data["customer_id"] = 214
    ticket = Ticket(**data)
    db.add(ticket)
    await db.flush()
    await db.commit()
    await db.refresh(ticket)
    return ok({"id": ticket.id, "title": ticket.title})


@ticket_router.post("/{ticket_id}/transition")
async def transition_ticket(
    ticket_id: int,
    body: TicketTransition,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    ticket = await db.get(Ticket, ticket_id)
    if ticket is None or ticket.deleted_at is not None:
        raise NotFoundError("工单不存在")
    await transition_status(
        db,
        ticket,
        body.target_status,
        guard=assert_can_transition_ticket,
        aggregate_type="Ticket",
        actor=user["user_id"],
        reason=body.reason,
    )
    if body.target_status == "resolved":
        ticket.resolved_at = datetime.now(timezone.utc)
    elif body.target_status == "open":
        ticket.resolved_at = None
    await db.commit()
    return ok({"id": ticket.id, "status": ticket.status})
