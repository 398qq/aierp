"""Background job scheduler — periodic AI enrichment, health checks, cleanup."""

import logging
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import func, select

from app.database import async_session

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


# ============================================================
# Job definitions
# ============================================================


async def _refresh_sales_insights():
    """Re-enrich opportunities/quotations modified in the last 24h that may have stale insights."""
    try:
        from app.models.sales import Opportunity, Quotation

        async with async_session() as db:
            cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
            opps = (
                (
                    await db.execute(
                        select(Opportunity).where(
                            Opportunity.deleted_at.is_(None),
                            Opportunity.updated_at >= cutoff,
                        )
                    )
                )
                .scalars()
                .all()
            )
            quotes = (
                (
                    await db.execute(
                        select(Quotation).where(
                            Quotation.deleted_at.is_(None),
                            Quotation.updated_at >= cutoff,
                        )
                    )
                )
                .scalars()
                .all()
            )
            if not opps and not quotes:
                return
            from app.services.sales_ai_service import (
                enrich_opportunity,
                enrich_quotation,
            )

            for opp in opps:
                try:
                    await enrich_opportunity(db, opp)
                except Exception as e:
                    logger.warning(f"scheduler: enrich opp #{opp.id} failed: {e}")
            for quote in quotes:
                try:
                    await enrich_quotation(db, quote)
                except Exception as e:
                    logger.warning(f"scheduler: enrich quote #{quote.id} failed: {e}")
            if opps or quotes:
                logger.info(
                    f"scheduler: refreshed {len(opps)} opportunities, {len(quotes)} quotations"
                )
    except Exception as e:
        logger.error(f"scheduler: refresh_sales_insights failed: {e}")


async def _check_overdue_payments():
    """Create notifications for overdue payments."""
    try:
        from app.models.finance import Invoice, Notification
        from app.services.notification_service import create_notification

        async with async_session() as db:
            overdue = (
                (
                    await db.execute(
                        select(Invoice).where(
                            Invoice.deleted_at.is_(None),
                            Invoice.status == "overdue",
                        )
                    )
                )
                .scalars()
                .all()
            )
            for inv in overdue:
                exists = (
                    await db.execute(
                        select(func.count(Notification.id)).where(
                            Notification.type == "overdue",
                            Notification.related_id == inv.id,
                            Notification.created_at
                            >= datetime.now(timezone.utc).replace(
                                hour=0, minute=0, second=0, microsecond=0
                            ),
                        )
                    )
                ).scalar() or 0
                if exists == 0:
                    await create_notification(
                        db,
                        user_id=1,
                        type="overdue",
                        title=f"发票 {inv.invoice_no or '#' + str(inv.id)} 已逾期",
                        content=f"金额 ¥{inv.amount:,.2f}，请及时处理。",
                        related_id=inv.id,
                    )
    except Exception as e:
        logger.error(f"scheduler: check_overdue_payments failed: {e}")


async def _check_target_progress():
    """Warn on targets significantly behind schedule."""
    try:
        from app.models.finance import SalesTarget
        from app.services.notification_service import create_notification

        async with async_session() as db:
            targets = (
                (
                    await db.execute(
                        select(SalesTarget).where(
                            SalesTarget.deleted_at.is_(None),
                            SalesTarget.status == "active",
                            SalesTarget.period_end > datetime.now(timezone.utc),
                        )
                    )
                )
                .scalars()
                .all()
            )
            for t in targets:
                if t.target_amount <= 0:
                    continue
                elapsed_pct = 0.5  # default: assume halfway
                if t.period_start and t.period_end:
                    total_duration = (t.period_end - t.period_start).total_seconds()
                    if total_duration > 0:
                        elapsed = (
                            datetime.now(timezone.utc) - t.period_start
                        ).total_seconds()
                        elapsed_pct = max(0, min(1, elapsed / total_duration))
                expected = t.target_amount * elapsed_pct
                if t.actual_amount < expected * 0.5:  # less than 50% of expected
                    await create_notification(
                        db,
                        user_id=t.user_id,
                        type="target_warning",
                        title="销售目标进度落后",
                        content=f"目标 ¥{t.target_amount:,.2f}，当前完成 ¥{t.actual_amount:,.2f}（{t.actual_amount / t.target_amount * 100:.1f}%），预期进度 {elapsed_pct * 100:.1f}%",
                        related_id=t.id,
                    )
    except Exception as e:
        logger.error(f"scheduler: check_target_progress failed: {e}")


async def _check_contract_expiry():
    """Alert on contracts expiring within 30 days."""
    try:
        from datetime import timedelta
        from app.models.finance import Contract
        from app.services.notification_service import create_notification

        async with async_session() as db:
            soon = datetime.now(timezone.utc) + timedelta(days=30)
            contracts = (
                (
                    await db.execute(
                        select(Contract).where(
                            Contract.deleted_at.is_(None),
                            Contract.status.in_(["signed", "active"]),
                            Contract.expire_date.isnot(None),
                            Contract.expire_date <= soon,
                            Contract.expire_date > datetime.now(timezone.utc),
                        )
                    )
                )
                .scalars()
                .all()
            )
            for ct in contracts:
                await create_notification(
                    db,
                    user_id=1,
                    type="contract_expiry",
                    title=f"合同 {ct.contract_no or '#' + str(ct.id)} 即将到期",
                    content=f"{ct.title}，到期日 {ct.expire_date.strftime('%Y-%m-%d') if ct.expire_date else '?'}",
                    related_id=ct.id,
                )
    except Exception as e:
        logger.error(f"scheduler: check_contract_expiry failed: {e}")


async def _refresh_embeddings():
    """Re-embed all entities (customers, products, suppliers) missing embeddings."""
    try:
        from app.services.ai import EmbeddingService

        async with async_session() as db:
            c_stats = await EmbeddingService.index_all(db)
            p_stats = await EmbeddingService.index_all_products(db)
            s_stats = await EmbeddingService.index_all_suppliers(db)
            await db.commit()
            total = (
                c_stats.get("indexed", 0)
                + p_stats.get("indexed", 0)
                + s_stats.get("indexed", 0)
            )
            if total:
                logger.info(
                    f"scheduler: embedded {total} entities (c:{c_stats['indexed']} p:{p_stats['indexed']} s:{s_stats['indexed']})"
                )
    except Exception as e:
        logger.error(f"scheduler: refresh_embeddings failed: {e}")


async def _run_watchtower_scan():
    """Cross-domain anomaly scan — creates notifications for detected issues."""
    try:
        from app.services.ai.agents import WatchtowerService

        async with async_session() as db:
            result = await WatchtowerService.scan_and_notify(db)
            await db.commit()
            if result["findings"]:
                logger.info(
                    f"scheduler: watchtower found {result['findings']} anomalies, created {result['notifications_created']} notifications"
                )
    except Exception as e:
        logger.error(f"scheduler: watchtower_scan failed: {e}")


async def _populate_customer_insights():
    """Daily batch job: run RFM analysis + churn risk for all customers with order history."""
    try:
        from app.services.ai import CustomerAgent
        from app.models.customer import Customer
        from app.models.sales import SalesOrder
        from sqlalchemy import func

        async with async_session() as db:
            # Get customers with orders in last 365 days
            d365 = datetime.now(timezone.utc) - timedelta(days=365)
            active_ids = (
                (
                    await db.execute(
                        select(SalesOrder.customer_id.distinct()).where(
                            SalesOrder.deleted_at.is_(None),
                            SalesOrder.created_at >= d365,
                        )
                    )
                )
                .scalars()
                .all()
            )

            customers = (
                (
                    await db.execute(
                        select(Customer)
                        .where(
                            Customer.id.in_(active_ids),
                            Customer.deleted_at.is_(None),
                        )
                        .limit(50)  # Batch limit to avoid overwhelming AI API
                    )
                )
                .scalars()
                .all()
            )

            updated = 0
            for cust in customers:
                try:
                    order_total = (
                        await db.execute(
                            select(
                                func.count(SalesOrder.id),
                                func.coalesce(func.sum(SalesOrder.total_amount), 0),
                                func.max(SalesOrder.created_at),
                            ).where(
                                SalesOrder.customer_id == cust.id,
                                SalesOrder.deleted_at.is_(None),
                            )
                        )
                    ).first()

                    customer_data = {
                        "name": cust.name,
                        "industry": cust.industry or "未知",
                        "level": cust.level or "C",
                        "region": cust.region or "未知",
                        "order_count": int(order_total[0]) if order_total else 0,
                        "total_revenue": float(order_total[1]) if order_total else 0,
                        "last_order_date": str(order_total[2])
                        if order_total and order_total[2]
                        else "无",
                        "last_contact": str(cust.last_contacted_at)
                        if cust.last_contacted_at
                        else "无",
                    }

                    rfm = await CustomerAgent.rfm_analysis(customer_data)
                    churn = await CustomerAgent.churn_risk(customer_data)

                    cust.ai_insights = {
                        "rfm": rfm,
                        "churn_risk": churn,
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                    }
                    await db.flush()
                    updated += 1
                except Exception as e:
                    logger.warning(
                        f"scheduler: insight population for customer #{cust.id} failed: {e}"
                    )

            await db.commit()
            if updated:
                logger.info(f"scheduler: populated insights for {updated} customers")
    except Exception as e:
        logger.error(f"scheduler: populate_customer_insights failed: {e}")


async def _generate_daily_report():
    """Generate and store daily cross-domain report."""
    try:
        from datetime import datetime, timezone
        from sqlalchemy import func, select
        from app.models.sales import SalesOrder
        from app.models.customer import Customer
        from app.models.product import Inventory
        from app.models.finance import Notification
        from app.models.transaction import Payment
        from app.services.notification_service import create_notification

        async with async_session() as db:
            now = datetime.now(timezone.utc)
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            today = now.strftime("%Y-%m-%d")

            exists = (
                await db.execute(
                    select(func.count(Notification.id)).where(
                        Notification.type == "daily_report",
                        Notification.created_at >= today_start,
                    )
                )
            ).scalar() or 0
            if exists > 0:
                return

            # Metrics
            today_orders = (
                await db.execute(
                    select(
                        func.count(SalesOrder.id),
                        func.coalesce(func.sum(SalesOrder.total_amount), 0),
                    ).where(
                        SalesOrder.deleted_at.is_(None),
                        SalesOrder.created_at >= today_start,
                    )
                )
            ).first()
            orders_count = today_orders[0] if today_orders else 0
            orders_amount = float(today_orders[1]) if today_orders else 0.0

            new_cust = (
                await db.execute(
                    select(func.count(Customer.id)).where(
                        Customer.deleted_at.is_(None),
                        Customer.created_at >= today_start,
                    )
                )
            ).scalar() or 0

            low_stock = (
                await db.execute(
                    select(func.count(Inventory.id)).where(
                        Inventory.deleted_at.is_(None),
                        Inventory.quantity <= Inventory.safety_stock,
                        Inventory.quantity > 0,
                    )
                )
            ).scalar() or 0
            out_of_stock = (
                await db.execute(
                    select(func.count(Inventory.id)).where(
                        Inventory.deleted_at.is_(None), Inventory.quantity <= 0
                    )
                )
            ).scalar() or 0

            today_payments = (
                await db.execute(
                    select(
                        func.count(Payment.id),
                        func.coalesce(func.sum(Payment.amount), 0),
                    ).where(
                        Payment.deleted_at.is_(None), Payment.created_at >= today_start
                    )
                )
            ).first()
            payments_count = today_payments[0] if today_payments else 0
            payments_amount = float(today_payments[1]) if today_payments else 0.0

            # AI summary
            try:
                from app.services.ai.client import ai_client

                prompt = (
                    f"Today's ERP snapshot ({today}):\n"
                    f"- New orders: {orders_count}, revenue: ¥{orders_amount:,.2f}\n"
                    f"- New customers: {new_cust}\n"
                    f"- Payments received: {payments_count}, amount: ¥{payments_amount:,.2f}\n"
                    f"- Low stock products: {low_stock}\n"
                    f"- Out of stock products: {out_of_stock}\n\n"
                    f"Write a 2-3 sentence executive daily briefing in Chinese."
                )
                schema = {
                    "summary": "string, 2-3 sentence executive briefing in Chinese",
                    "mood": "string: 良好/一般/需关注",
                    "top_action": "string, single most important action today",
                }
                ai = await ai_client.chat_structured(
                    [
                        {
                            "role": "system",
                            "content": "你是一个ERP日报助手，擅长用简洁的语言总结每日经营状况。",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    schema,
                )
                summary = ai.get("summary", "")
                mood = ai.get("mood", "一般")
                top_action = ai.get("top_action", "")
            except Exception as e:
                logger.warning(f"Daily report AI failed: {e}")
                summary = "AI摘要暂不可用"
                mood = "一般"
                top_action = ""

            await create_notification(
                db,
                user_id=1,
                type="daily_report",
                title=f"每日经营报告 — {today} ({mood})",
                content=(
                    f"{summary}\n\n"
                    f"今日订单: {orders_count} 单 / ¥{orders_amount:,.2f}\n"
                    f"新客户: {new_cust} | 收款: {payments_count} 笔 / ¥{payments_amount:,.2f}\n"
                    f"低库存: {low_stock} | 缺货: {out_of_stock}\n\n"
                    f"建议行动: {top_action}"
                ),
            )
            await db.commit()
            logger.info(f"scheduler: daily report generated for {today}")
    except Exception as e:
        logger.error(f"scheduler: daily_report failed: {e}")


async def _cleanup_old_notifications():
    """Soft-delete notifications older than 90 days."""
    try:
        from app.services.notification_service import delete_old_notifications

        async with async_session() as db:
            deleted = await delete_old_notifications(db, days=90)
            if deleted:
                logger.info(f"scheduler: cleaned up {deleted} old notifications")
    except Exception as e:
        logger.error(f"scheduler: cleanup_old_notifications failed: {e}")


async def _auto_expire_schemes():
    """Daily: expire schemes past effective_to + warn 7 days before expiry."""
    try:
        from datetime import date, timedelta
        from app.services.commission_scheme_service import auto_expire_schemes
        from app.models.commission_scheme import CommissionScheme
        from app.services.notification_service import create_notification

        async with async_session() as db:
            # 1. Auto-expire
            expired = await auto_expire_schemes(db)
            if expired:
                logger.info(f"scheduler: auto-expired {expired} commission schemes")

            # 2. Notify 7 days before expiry
            warning_date = date.today() + timedelta(days=7)
            about_to_expire = (
                (
                    await db.execute(
                        select(CommissionScheme).where(
                            CommissionScheme.deleted_at.is_(None),
                            CommissionScheme.status == "active",
                            CommissionScheme.effective_to.isnot(None),
                            CommissionScheme.effective_to == warning_date,
                        )
                    )
                )
                .scalars()
                .all()
            )
            for scheme in about_to_expire:
                await create_notification(
                    db,
                    user_id=1,  # Notify admin
                    type="scheme_expiry_warning",
                    title=f"提成方案「{scheme.name}」即将到期",
                    content=(
                        f"方案 {scheme.name} 将于 {scheme.effective_to} 到期。"
                        f"请及时准备新方案，避免影响销售员佣金计算。"
                    ),
                    related_id=scheme.id,
                )
                logger.info(
                    "scheduler: expiry warning for scheme %s (id=%s, expires %s)",
                    scheme.name,
                    scheme.id,
                    scheme.effective_to,
                )
            await db.commit()
    except Exception as e:
        logger.error(f"scheduler: auto_expire_schemes failed: {e}")


async def _run_auto_assign_job() -> dict:
    """Auto-assign public-sea customers based on AssignmentRules."""
    try:
        from app.models.customer import AssignmentRule, Customer, CustomerOwnerLog
        from sqlalchemy.orm import selectinload

        async with async_session() as db:
            rules = (
                (
                    await db.execute(
                        select(AssignmentRule)
                        .where(
                            AssignmentRule.deleted_at.is_(None),
                            AssignmentRule.is_enabled == True,  # noqa: E712
                        )
                        .options(selectinload(AssignmentRule.conditions))
                        .order_by(AssignmentRule.priority.asc())
                    )
                )
                .scalars()
                .all()
            )

            if not rules:
                return {"assigned": 0, "rules_checked": 0}

            # Get all public-sea customers (no owner)
            customers = (
                (
                    await db.execute(
                        select(Customer).where(
                            Customer.deleted_at.is_(None),
                            Customer.owner.is_(None),
                        )
                    )
                )
                .scalars()
                .all()
            )

            if not customers:
                return {"assigned": 0, "rules_checked": len(rules)}

            assigned_count = 0
            operator = "system"

            for rule in rules:
                # Check if assigned_to has reached their limit
                current_count = (
                    (
                        await db.execute(
                            select(Customer).where(
                                Customer.owner == rule.assigned_to,
                                Customer.deleted_at.is_(None),
                            )
                        )
                    )
                    .scalars()
                    .all()
                )
                current_assigned = len(current_count)

                if (
                    rule.max_customers is not None
                    and current_assigned >= rule.max_customers
                ):
                    continue  # skip rule — target user is at capacity

                for customer in customers:
                    if customer.owner is not None:
                        continue  # already assigned (concurrent)

                    if (
                        rule.max_customers is not None
                        and current_assigned >= rule.max_customers
                    ):
                        break  # capacity reached for this rule

                    # Evaluate conditions
                    matched = _evaluate_assignment_conditions(customer, rule)
                    if not matched:
                        continue

                    # Assign
                    customer.owner = rule.assigned_to
                    log = CustomerOwnerLog(
                        customer_id=customer.id,
                        from_owner=None,
                        to_owner=rule.assigned_to,
                        action_type="auto_assign",
                        operator=operator,
                        reason=f"自动分配规则: {rule.name}",
                    )
                    db.add(log)
                    assigned_count += 1
                    current_assigned += 1

            await db.commit()
            if assigned_count:
                logger.info(
                    f"scheduler: auto_assign — assigned {assigned_count} customers "
                    f"across {len(rules)} rules"
                )
            return {"assigned": assigned_count, "rules_checked": len(rules)}
    except Exception as e:
        logger.error(f"scheduler: auto_assign failed: {e}")
        return {"assigned": 0, "rules_checked": 0, "error": str(e)}


def _evaluate_assignment_conditions(customer, rule) -> bool:
    """Evaluate whether a customer matches all/any conditions of an assignment rule."""
    if not rule.conditions:
        return True  # no conditions = match all

    results = []
    for cond in rule.conditions:
        field_value = getattr(customer, cond.field, None)
        if field_value is None:
            results.append(False)
            continue

        field_value = str(field_value)
        if cond.operator == "equals":
            results.append(field_value == cond.value)
        elif cond.operator == "in":
            values = [v.strip() for v in cond.value.split(",")]
            results.append(field_value in values)
        elif cond.operator == "contains":
            results.append(cond.value in field_value)
        elif cond.operator == "not_empty":
            results.append(bool(field_value))
        else:
            results.append(False)

    if rule.condition_logic == "any":
        return any(results)
    return all(results)


def _release_customer_owner(
    db,
    customer,
    rule,
    reason: str,
    operator: str,
    username_to_user_id: dict[str, int],
) -> None:
    """Release ``customer``'s owner for ``rule``: clear owner, log, optionally
    transition ``status`` and notify the outgoing owner.

    Status transition and notification are best-effort — an illegal state
    transition or unresolvable owner username must not abort the release.
    """
    from app.domain.shared.errors import InvalidStateTransition
    from app.domain.states import assert_can_transition_customer
    from app.models.customer import CustomerOwnerLog
    from app.models.finance import Notification

    from_owner = customer.owner
    customer.owner = None

    if rule.target_status:
        try:
            assert_can_transition_customer(customer.status, rule.target_status)
            customer.status = rule.target_status
        except InvalidStateTransition:
            logger.info(
                "scheduler: owner_release_check — skip illegal status transition "
                "%s → %s for customer #%d (rule: %s)",
                customer.status,
                rule.target_status,
                customer.id,
                rule.name,
            )

    db.add(
        CustomerOwnerLog(
            customer_id=customer.id,
            from_owner=from_owner,
            to_owner=None,
            action_type="auto_release",
            operator=operator,
            reason=reason,
        )
    )

    if rule.notify_owner and from_owner:
        owner_user_id = username_to_user_id.get(from_owner)
        if owner_user_id is not None:
            db.add(
                Notification(
                    user_id=owner_user_id,
                    type="owner_release",
                    title=f"客户「{customer.name}」已自动释放",
                    content=reason,
                    related_id=customer.id,
                )
            )


async def _run_owner_release_check_job():
    """Auto-release customer owners who have no follow-ups / orders beyond threshold days.

    Reads all enabled ReleaseRules from DB and applies them.
    """
    try:
        from datetime import timedelta
        from app.models.customer import ReleaseRule, Customer
        from app.models.customer import CustomerFollowUp
        from app.models.sales import SalesOrder
        from app.models.user import User

        async with async_session() as db:
            rules = (
                (
                    await db.execute(
                        select(ReleaseRule)
                        .where(
                            ReleaseRule.deleted_at.is_(None),
                            ReleaseRule.is_enabled == True,  # noqa: E712
                        )
                        .order_by(ReleaseRule.priority.asc())
                    )
                )
                .scalars()
                .all()
            )

            if not rules:
                return

            now = datetime.now(timezone.utc)
            released_count = 0

            customers = (
                (
                    await db.execute(
                        select(Customer).where(
                            Customer.deleted_at.is_(None),
                            Customer.owner.isnot(None),
                            Customer.owner != "",
                        )
                    )
                )
                .scalars()
                .all()
            )

            username_to_user_id = {
                u.username: u.id
                for u in (
                    await db.execute(select(User).where(User.deleted_at.is_(None)))
                )
                .scalars()
                .all()
            }

            operator = "system"

            for rule in rules:
                cutoff = now - timedelta(days=rule.condition_days)
                for customer in customers:
                    if customer.owner is None or customer.owner == "":
                        continue

                    if rule.rule_type == "no_followup":
                        # Check most recent follow-up completed_at
                        last_fu = (
                            await db.execute(
                                select(CustomerFollowUp)
                                .where(
                                    CustomerFollowUp.customer_id == customer.id,
                                    CustomerFollowUp.deleted_at.is_(None),
                                    CustomerFollowUp.completed_at.isnot(None),
                                )
                                .order_by(CustomerFollowUp.completed_at.desc())
                                .limit(1)
                            )
                        ).scalar_one_or_none()

                        if (
                            last_fu
                            and last_fu.completed_at
                            and last_fu.completed_at >= cutoff
                        ):
                            continue  # has recent follow-up, skip

                        # Also check created_at as a proxy for "new customer with no follow-up"
                        if customer.created_at and customer.created_at >= cutoff:
                            continue  # brand new customer, give grace period

                        # Release this customer
                        _release_customer_owner(
                            db,
                            customer,
                            rule,
                            reason=f"超过{rule.condition_days}天无跟进记录（规则: {rule.name}）",
                            operator=operator,
                            username_to_user_id=username_to_user_id,
                        )
                        released_count += 1

                    elif rule.rule_type == "no_order":
                        last_order = (
                            await db.execute(
                                select(SalesOrder)
                                .where(
                                    SalesOrder.customer_id == customer.id,
                                    SalesOrder.deleted_at.is_(None),
                                    SalesOrder.status == "completed",
                                )
                                .order_by(SalesOrder.order_date.desc().nulls_last())
                                .limit(1)
                            )
                        ).scalar_one_or_none()

                        if (
                            last_order
                            and last_order.order_date
                            and last_order.order_date >= cutoff
                        ):
                            continue

                        # Skip brand-new customers
                        if customer.created_at and customer.created_at >= cutoff:
                            continue

                        _release_customer_owner(
                            db,
                            customer,
                            rule,
                            reason=f"超过{rule.condition_days}天无新订单（规则: {rule.name}）",
                            operator=operator,
                            username_to_user_id=username_to_user_id,
                        )
                        released_count += 1

            if released_count:
                await db.commit()
                logger.info(
                    f"scheduler: owner_release_check — released {released_count} customers "
                    f"across {len(rules)} rules"
                )
            else:
                await db.commit()
    except Exception as e:
        logger.error(f"scheduler: owner_release_check failed: {e}")


async def _run_customer_status_job():
    """Daily customer lifecycle status transitions (cron 02:00).

    - Active/Converted/VIP with no interaction > 90 days → inactive
    - Converted with 12-month revenue > ¥500,000 → VIP
    """
    try:
        from app.services.customer_state_service import run_customer_status_job

        async with async_session() as db:
            result = await run_customer_status_job(db)
            if result["total_checked"] > 0:
                logger.info(
                    "scheduler: customer status job — vip=%d inactive=%d",
                    result["to_vip"],
                    result["to_inactive"],
                )
    except Exception as e:
        logger.error(f"scheduler: customer_status_job failed: {e}")


async def _check_batch_expiry():
    """Alert warehouse managers about expiring/expired inventory batches.

    Mirrors ``_check_contract_expiry`` pattern. Scans Stage 2's expiry
    buckets via :func:`expiry_alert_service.scan` and creates one
    notification per affected batch. Only the most urgent buckets
    (expired + 7d) are notified today — 30d/90d can become a separate
    job if earlier warnings are needed.

    Dedup note: no explicit dedup. Job runs daily, so one notification
    per batch per day. If the job is moved to a higher frequency, add
    a "last 23h" check on (related_id, type) to avoid spam.
    """
    try:
        from app.services.expiry_alert_service import expiry_alert_service
        from app.services.notification_service import create_notification

        async with async_session() as db:
            # expired + 7d only — most urgent buckets
            scan_result = await expiry_alert_service.scan(
                db, buckets=["expired", "7d"], limit_per_bucket=100
            )
            notified = 0
            for bucket_name in ("expired", "7d"):
                for batch in scan_result.get(bucket_name, []):
                    days = batch["days_until_expiry"] or 0
                    if days <= 0:
                        title = f"批次 {batch['batch_no']} 已过期 {abs(days)} 天"
                    else:
                        title = f"批次 {batch['batch_no']} {days} 天内到期"
                    content = (
                        f"产品 ID: {batch['product_id']} | "
                        f"剩余: {batch['quantity']} | "
                        f"有效期: {batch['expiry_date']}"
                    )
                    await create_notification(
                        db,
                        user_id=1,  # admin (TODO: per-warehouse routing)
                        type="batch_expiry_warning",
                        title=title,
                        content=content,
                        related_id=batch["id"],
                    )
                    notified += 1
            if notified:
                logger.info(
                    "scheduler: batch_expiry notified %d batches (expired+7d)",
                    notified,
                )
    except Exception as e:
        logger.error(f"scheduler: check_batch_expiry failed: {e}")


# ============================================================
# Startup / Shutdown
# ============================================================


def start():
    scheduler.add_job(
        _refresh_sales_insights,
        "interval",
        hours=6,
        id="refresh_insights",
        misfire_grace_time=300,
    )
    scheduler.add_job(
        _check_overdue_payments,
        "interval",
        hours=12,
        id="check_overdue",
        misfire_grace_time=300,
    )
    scheduler.add_job(
        _check_target_progress,
        "interval",
        hours=24,
        id="check_targets",
        misfire_grace_time=600,
    )
    scheduler.add_job(
        _check_contract_expiry,
        "interval",
        hours=24,
        id="check_contracts",
        misfire_grace_time=600,
    )
    scheduler.add_job(
        _cleanup_old_notifications,
        "interval",
        hours=24,
        id="cleanup_notifications",
        misfire_grace_time=600,
    )
    scheduler.add_job(
        _refresh_embeddings,
        "interval",
        hours=24,
        id="refresh_embeddings",
        misfire_grace_time=600,
    )
    scheduler.add_job(
        _run_watchtower_scan,
        "interval",
        hours=4,
        id="watchtower_scan",
        misfire_grace_time=300,
    )
    scheduler.add_job(
        _populate_customer_insights,
        "interval",
        hours=24,
        id="populate_insights",
        misfire_grace_time=600,
    )
    scheduler.add_job(
        _generate_daily_report,
        "cron",
        hour=18,
        minute=0,
        id="daily_report",
        misfire_grace_time=600,
    )
    scheduler.add_job(
        _run_customer_status_job,
        "cron",
        hour=2,
        minute=0,
        id="customer_status",
        misfire_grace_time=3600,
    )
    scheduler.add_job(
        _run_owner_release_check_job,
        "cron",
        hour=2,
        minute=30,
        id="owner_release_check",
        misfire_grace_time=3600,
    )
    scheduler.add_job(
        _run_auto_assign_job,
        "cron",
        hour=3,
        minute=0,
        id="auto_assign",
        misfire_grace_time=3600,
    )
    scheduler.add_job(
        _auto_expire_schemes,
        "cron",
        hour=2,
        minute=5,  # 5 min after customer_status to spread load
        id="auto_expire_schemes",
        misfire_grace_time=3600,
    )
    scheduler.add_job(
        _check_batch_expiry,
        "interval",
        hours=24,
        id="check_batch_expiry",
        misfire_grace_time=600,
    )
    scheduler.start()
    logger.info("Scheduler started with 13 jobs")


def shutdown():
    scheduler.shutdown(wait=False)
    logger.info("Scheduler shut down")
