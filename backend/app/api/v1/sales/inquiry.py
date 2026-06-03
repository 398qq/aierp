"""Sales API — inquiry auto-reply.

AI-powered endpoint that:
- Parses MPN/brand mentions from inquiry text
- Matches against the product catalog
- Generates a professional reply (saved to DB)
- Returns reply + matched products + CRM summary

Delegated to ``app.services.sales_ai_service.inquiry_auto_reply``.
"""

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.schemas.common import ok
from app.schemas.sales import InquiryAutoReplyRequest

logger = logging.getLogger(__name__)

router = APIRouter(tags=["sales:inquiry"])


@router.post("/inquiry/auto-reply", response_model=dict)
async def inquiry_auto_reply(
    body: InquiryAutoReplyRequest,
    db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user),
):
    from app.services.sales_ai_service import inquiry_auto_reply as svc_auto_reply
    result = await svc_auto_reply(db, body.model_dump())
    return ok(result)
