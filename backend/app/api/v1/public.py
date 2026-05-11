"""Public API — no authentication required."""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.common import fail, ok
from app.schemas.sales import InquiryAutoReplyRequest
from app.services.sales_ai_service import inquiry_auto_reply

logger = logging.getLogger(__name__)

router = APIRouter(tags=["public"])


async def _send_wecom_notification(inquiry_id: int, contact_name: str,
                                    contact_info: str, inquiry_text: str,
                                    reply_text: str, summary: str) -> None:
    """
    Send WeCom/WeChat webhook notification to sales team.
    Falls back to logging if webhook URL is not configured.
    """
    try:
        from app.config import settings
        webhook_url = getattr(settings, "WECOM_WEBHOOK_URL", None)
        if not webhook_url:
            logger.warning("[Public Inquiry] WECOM_WEBHOOK_URL not configured, skipping notification")
            return

        # Build message payload
        contact_line = f"联系人：{contact_name}" if contact_name else ""
        info_line = f"联系方式：{contact_info}" if contact_info else ""

        content_lines = [
            "📩 **新客户询价** (Portal)",
            "",
            f"询价内容：{inquiry_text[:200]}",
            "",
        ]
        if contact_line:
            content_lines.append(contact_line)
        if info_line:
            content_lines.append(info_line)

        content_lines.extend([
            "",
            f"**AI 回复摘要**：{summary}",
            "",
            f"⏰ 时间：{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}",
            f"🔗 InquiryID：{inquiry_id}",
        ])

        payload = {
            "msgtype": "markdown",
            "markdown": {
                "content": "\n".join(content_lines),
            },
        }

        import httpx
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(webhook_url, json=payload)
            if resp.status_code == 200:
                logger.info(f"[Public Inquiry] WeCom notification sent for inquiry {inquiry_id}")
            else:
                logger.warning(f"[Public Inquiry] WeCom notification failed: {resp.status_code} {resp.text}")

    except Exception as e:
        logger.exception(f"[Public Inquiry] Failed to send WeCom notification: {e}")


@router.post("/public/inquiry")
async def public_inquiry(
    body: InquiryAutoReplyRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Public inquiry endpoint — no auth required.

    Accepts inquiry from website portal, runs AI auto-reply,
    persists the inquiry record, and notifies sales via WeCom.
    """
    # Force channel to "portal" for public submissions
    req_data = body.model_dump()
    req_data["channel"] = "portal"

    try:
        result = await inquiry_auto_reply(db, req_data)
        await db.commit()
    except Exception:
        logger.exception("public_inquiry failed")
        return fail("询价处理失败，请稍后重试", 500)

    # Send WeCom notification to sales
    inquiry_id = result.get("inquiry_id")
    reply_text = result.get("reply_text", "")
    summary = result.get("summary", "")

    # Truncate reply for notification
    _ = reply_text[:100] + "..." if len(reply_text) > 100 else reply_text

    await _send_wecom_notification(
        inquiry_id=inquiry_id,
        contact_name=body.contact_name or "",
        contact_info=body.contact_info or "",
        inquiry_text=body.inquiry_text,
        reply_text=reply_text,
        summary=summary,
    )

    return ok(result)
