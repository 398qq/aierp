"""Watchtower Agent — cross-domain anomaly scanner.

Scans inventory, finance, sales, and customer domains for high-priority
issues (low stock, overdue invoices, stale opportunities, silent A/B
customers) and produces a flat list of findings. Used by the daily
watchtower job and the watchtower dashboard.
"""

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select

from app.services.ai.agent_modules.base import BaseAgent

logger = logging.getLogger(__name__)


class WatchtowerService(BaseAgent):
    name = "watchtower"
    description = "Cross-domain anomaly scanner — finds low stock, overdue invoices, stale opps, silent A/B customers."

    SEVERITY_RANK = {"low": 0, "medium": 1, "high": 2, "critical": 3}

    @staticmethod
    async def scan_all(db) -> list[dict]:
        """Scan all domains for anomalies and return findings.

        Each finding is a dict with keys: domain, severity, title, detail.
        Severity is one of: low, medium, high, critical.
        """
        from app.models.customer import Customer
        from app.models.finance import Invoice
        from app.models.product import Inventory
        from app.models.sales import Opportunity

        findings: list[dict] = []
        now = datetime.now(timezone.utc)

        # 1. Inventory: low stock items
        low_stock = (await db.execute(
            select(func.count(Inventory.id)).where(
                Inventory.deleted_at.is_(None),
                Inventory.quantity <= Inventory.safety_stock,
                Inventory.quantity > 0,
            )
        )).scalar() or 0
        if low_stock > 0:
            findings.append({
                "domain": "库存",
                "severity": "high" if low_stock > 10 else "medium",
                "title": f"低库存预警：{low_stock} 个SKU",
                "detail": f"当前有 {low_stock} 个产品的库存低于安全库存线",
            })

        # 2. Inventory: dead stock (no movement in 180d)
        d180 = now - timedelta(days=180)
        dead = (await db.execute(
            select(func.count(Inventory.id)).where(
                Inventory.deleted_at.is_(None),
                Inventory.quantity > 0,
                Inventory.updated_at < d180,
            )
        )).scalar() or 0
        if dead > 0:
            findings.append({
                "domain": "库存",
                "severity": "medium",
                "title": f"滞销库存：{dead} 个SKU",
                "detail": f"{dead} 个产品超过180天无变动",
            })

        # 3. Finance: overdue invoices
        overdue = (await db.execute(
            select(func.count(Invoice.id), func.coalesce(func.sum(Invoice.amount), 0)).where(
                Invoice.deleted_at.is_(None),
                Invoice.status == "overdue",
            )
        )).first()
        if overdue and overdue[0] > 0:
            findings.append({
                "domain": "财务",
                "severity": "critical" if float(overdue[1]) > 100_000 else "high",
                "title": f"逾期发票：{overdue[0]} 张",
                "detail": f"逾期金额 ¥{float(overdue[1]):,.0f}",
            })

        # 4. Sales: stale opportunities
        d30 = now - timedelta(days=30)
        stale_opps = (await db.execute(
            select(func.count(Opportunity.id), func.coalesce(func.sum(Opportunity.amount), 0)).where(
                Opportunity.deleted_at.is_(None),
                Opportunity.status == "open",
                Opportunity.updated_at < d30,
            )
        )).first()
        if stale_opps and stale_opps[0] > 0:
            findings.append({
                "domain": "销售",
                "severity": "high" if stale_opps[0] > 5 else "medium",
                "title": f"停滞商机：{stale_opps[0]} 个",
                "detail": f"{stale_opps[0]} 个开放商机超过30天未更新，合计 ¥{float(stale_opps[1]):,.0f}",
            })

        # 5. Customer: no contact in 90 days for A/B tier
        d90 = now - timedelta(days=90)
        silent = (await db.execute(
            select(func.count(Customer.id)).where(
                Customer.deleted_at.is_(None),
                Customer.level.in_(["A", "B"]),
                Customer.last_contacted_at.isnot(None),
                Customer.last_contacted_at < d90,
            )
        )).scalar() or 0
        if silent > 0:
            findings.append({
                "domain": "客户",
                "severity": "medium",
                "title": f"长期未联系客户：{silent} 个",
                "detail": f"{silent} 个A/B级客户超过90天未联系",
            })

        # Sort: critical → high → medium → low, then by domain
        findings.sort(
            key=lambda f: (
                -WatchtowerService.SEVERITY_RANK.get(f["severity"], 0),
                f["domain"],
            )
        )
        return findings

    @staticmethod
    async def scan_and_notify(db) -> dict:
        """Scan all domains and create notification entries for findings.

        Returns: {"findings": int, "notifications_created": int}
        """
        from app.services.notification_service import create_notification

        findings = await WatchtowerService.scan_all(db)
        created = 0
        for f in findings:
            try:
                await create_notification(
                    db,
                    user_id=1,
                    type=f"watchtower_{f['domain']}",
                    title=f"[{f['severity'].upper()}] {f['title']}",
                    content=f["detail"],
                )
                created += 1
            except Exception as e:
                logger.warning("Watchtower notification creation failed: %s", e)

        if findings:
            summary_lines = [
                f"- [{f['severity']}] [{f['domain']}] {f['title']}" for f in findings
            ]
            try:
                await create_notification(
                    db,
                    user_id=1,
                    type="watchtower_summary",
                    title=f"Watchtower 扫描报告 — {len(findings)} 个预警",
                    content="\n".join(summary_lines),
                )
            except Exception as e:
                logger.warning("Watchtower summary creation failed: %s", e)

        return {"findings": len(findings), "notifications_created": created}

    @staticmethod
    def summarize(findings: list[dict]) -> dict:
        """Group findings by severity for dashboard display."""
        by_severity = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        by_domain: dict[str, int] = {}
        for f in findings:
            by_severity[f["severity"]] = by_severity.get(f["severity"], 0) + 1
            by_domain[f["domain"]] = by_domain.get(f["domain"], 0) + 1
        return {
            "total": len(findings),
            "by_severity": by_severity,
            "by_domain": by_domain,
        }
