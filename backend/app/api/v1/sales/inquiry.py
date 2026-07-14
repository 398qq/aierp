"""Sales API — inquiry auto-reply.

AI-powered endpoint that:
- Parses MPN/brand mentions from inquiry text
- Matches against the product catalog
- Generates a professional reply (saved to DB)
- Returns reply + matched products + CRM summary

Delegated to ``app.services.sales_ai_service.inquiry_auto_reply``.
"""

import logging
from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.database import get_db
from app.models.sales import Inquiry
from app.schemas.common import ok
from app.schemas.sales import InquiryAutoReplyRequest

logger = logging.getLogger(__name__)

router = APIRouter(tags=["sales:inquiry"])


@router.get("/inquiries", response_model=dict)
async def list_inquiries(
    limit: int = Query(10, ge=1, le=100),
    sort_by: Literal["created_at", "id"] = "created_at",
    order: Literal["asc", "desc"] = "desc",
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Return recent inquiries for the sales reply workbench."""
    sort_column = Inquiry.created_at if sort_by == "created_at" else Inquiry.id
    ordering = sort_column.asc() if order == "asc" else sort_column.desc()
    result = await db.execute(
        select(Inquiry)
        .options(selectinload(Inquiry.customer))
        .where(Inquiry.deleted_at.is_(None))
        .order_by(ordering)
        .limit(limit)
    )
    total = await db.scalar(
        select(func.count(Inquiry.id)).where(Inquiry.deleted_at.is_(None))
    )
    records = result.scalars().all()
    return ok(
        {
            "list": [
                {
                    "id": inquiry.id,
                    "inquiry_text": inquiry.inquiry_text,
                    "reply_text": inquiry.reply_text,
                    "confidence": inquiry.ai_confidence,
                    "customer_id": inquiry.customer_id,
                    "customer_name": inquiry.customer.name if inquiry.customer else None,
                    "contact_name": inquiry.contact_name,
                    "contact_info": inquiry.contact_info,
                    "channel": inquiry.channel,
                    "status": inquiry.status,
                    "created_at": inquiry.created_at,
                }
                for inquiry in records
            ],
            "total": total or 0,
        }
    )


@router.post("/inquiry/auto-reply", response_model=dict)
async def inquiry_auto_reply(
    body: InquiryAutoReplyRequest,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    from app.services.sales_ai_service import inquiry_auto_reply as svc_auto_reply

    result = await svc_auto_reply(db, body.model_dump())
    return ok(result)
