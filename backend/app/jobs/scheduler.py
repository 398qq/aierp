"""Background AI jobs — scheduled RFM scoring, churn prediction, alerts."""

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def run_rfm_batch():
    """Run RFM analysis on all active customers nightly."""
    from datetime import datetime, timezone

    from sqlalchemy import func, select

    from app.database import async_session
    from app.models.customer import Customer, CustomerFollowUp
    from app.models.sales import SalesOrder
    from app.services.ai import CustomerAgent

    logger.info("Starting nightly RFM batch analysis")
    async with async_session() as db:
        try:
            result = await db.execute(
                select(Customer).where(Customer.deleted_at.is_(None))
            )
            customers = result.scalars().all()
            updated = 0

            for customer in customers:
                try:
                    order_stats = (await db.execute(
                        select(
                            func.count(SalesOrder.id),
                            func.coalesce(func.sum(SalesOrder.total_amount), 0),
                            func.max(SalesOrder.created_at),
                        ).where(
                            SalesOrder.customer_id == customer.id,
                            SalesOrder.deleted_at.is_(None),
                        )
                    )).first()

                    last_fu = (await db.execute(
                        select(CustomerFollowUp).where(
                            CustomerFollowUp.customer_id == customer.id,
                            CustomerFollowUp.deleted_at.is_(None),
                        ).order_by(CustomerFollowUp.created_at.desc()).limit(1)
                    )).scalar_one_or_none()

                    data = {
                        "name": customer.name,
                        "industry": customer.industry or "",
                        "total_orders": order_stats[0] or 0,
                        "total_revenue": float(order_stats[1]),
                        "last_order_date": str(order_stats[2]) if order_stats[2] else None,
                        "last_contacted_at": str(customer.last_contacted_at) if customer.last_contacted_at else None,
                        "last_followup": str(last_fu.planned_at) if last_fu and last_fu.planned_at else None,
                    }
                    rfm_result = await CustomerAgent.rfm_analysis(data)

                    insights = customer.ai_insights or {}
                    insights["rfm"] = rfm_result
                    insights["rfm_updated_at"] = datetime.now(timezone.utc).isoformat()
                    customer.ai_insights = insights
                    updated += 1
                except Exception:
                    logger.warning(f"RFM failed for customer {customer.id}")

            await db.commit()
            logger.info(f"RFM batch complete: {updated}/{len(customers)} customers analyzed")
        except Exception:
            await db.rollback()
            logger.exception("RFM batch failed")


async def run_churn_prediction():
    """Run churn prediction with enriched multi-dimensional features."""
    from datetime import datetime, timedelta, timezone

    from sqlalchemy import func, select

    from app.database import async_session
    from app.models.customer import Customer, CustomerFollowUp
    from app.models.finance import PaymentRecord
    from app.models.sales import Opportunity, Quotation, SalesOrder
    from app.services.ai import CustomerAgent
    from app.services.customer_service import calc_health

    logger.info("Starting churn risk prediction")
    async with async_session() as db:
        try:
            result = await db.execute(
                select(Customer).where(Customer.deleted_at.is_(None))
            )
            customers = result.scalars().all()
            now = datetime.now(timezone.utc)
            d90 = now - timedelta(days=90)
            d180 = now - timedelta(days=180)
            updated = 0

            for customer in customers:
                try:
                    # Order stats with time windows
                    order_stats = (await db.execute(
                        select(
                            func.count(SalesOrder.id),
                            func.coalesce(func.sum(SalesOrder.total_amount), 0),
                            func.max(SalesOrder.created_at),
                            func.count(SalesOrder.id).filter(SalesOrder.created_at >= d90),
                            func.count(SalesOrder.id).filter(SalesOrder.created_at >= d180),
                        ).where(
                            SalesOrder.customer_id == customer.id,
                            SalesOrder.deleted_at.is_(None),
                        )
                    )).first()

                    # Opportunity pipeline
                    active_opps = (await db.execute(
                        select(func.count(Opportunity.id)).where(
                            Opportunity.customer_id == customer.id,
                            Opportunity.deleted_at.is_(None),
                            Opportunity.stage.in_(["lead", "qualification", "proposal", "negotiation"]),
                        )
                    )).scalar() or 0

                    active_quot = (await db.execute(
                        select(func.count(Quotation.id)).where(
                            Quotation.customer_id == customer.id,
                            Quotation.deleted_at.is_(None),
                            Quotation.status.in_(["draft", "sent"]),
                        )
                    )).scalar() or 0

                    # Credit utilization
                    credit_util = "无数据"
                    if customer.credit_limit and customer.credit_limit > 0:
                        outstanding = (await db.execute(
                            select(func.coalesce(func.sum(PaymentRecord.amount), 0)).where(
                                PaymentRecord.customer_id == customer.id,
                                PaymentRecord.deleted_at.is_(None),
                                PaymentRecord.status != "paid",
                            )
                        )).scalar() or 0
                        credit_util = f"{min(100, round(float(outstanding) / float(customer.credit_limit) * 100))}%"

                    # AR overdue: unpaid payments older than 30 days
                    ar_days = 0
                    thirty_days_ago = now - timedelta(days=30)
                    oldest_unpaid = (await db.execute(
                        select(PaymentRecord).where(
                            PaymentRecord.customer_id == customer.id,
                            PaymentRecord.deleted_at.is_(None),
                            PaymentRecord.status != "paid",
                            PaymentRecord.created_at < thirty_days_ago,
                        ).order_by(PaymentRecord.created_at.asc()).limit(1)
                    )).scalar_one_or_none()
                    if oldest_unpaid and oldest_unpaid.created_at:
                        ar_days = (now - oldest_unpaid.created_at.replace(tzinfo=timezone.utc)).days

                    # Health score
                    orders_for_h = (await db.execute(
                        select(SalesOrder).where(
                            SalesOrder.customer_id == customer.id, SalesOrder.deleted_at.is_(None)
                        )
                    )).scalars().all()
                    payments_for_h = (await db.execute(
                        select(PaymentRecord).where(
                            PaymentRecord.customer_id == customer.id, PaymentRecord.deleted_at.is_(None)
                        )
                    )).scalars().all()
                    h_score, h_label = calc_health(customer, list(orders_for_h), list(payments_for_h), now)

                    # Order trend
                    o90 = order_stats[3] or 0
                    o180 = order_stats[4] or 0
                    o_before = (o180 or 0) - (o90 or 0)
                    trend = "稳定"
                    if o90 > 0 and o_before > 0:
                        if o90 > o_before * 1.3:
                            trend = "增长"
                        elif o90 < o_before * 0.7:
                            trend = "下降"

                    last_fu = (await db.execute(
                        select(CustomerFollowUp).where(
                            CustomerFollowUp.customer_id == customer.id,
                            CustomerFollowUp.deleted_at.is_(None),
                        ).order_by(CustomerFollowUp.created_at.desc()).limit(1)
                    )).scalar_one_or_none()

                    data = {
                        "name": customer.name,
                        "industry": customer.industry or "",
                        "level": customer.level or "",
                        "lifecycle": customer.lifecycle or "未知",
                        "total_orders": order_stats[0] or 0,
                        "total_revenue": float(order_stats[1]) if order_stats[1] else 0,
                        "last_order_date": str(order_stats[2]) if order_stats[2] else None,
                        "orders_last_90d": o90,
                        "orders_last_180d": o180,
                        "order_trend": trend,
                        "last_followup_date": str(last_fu.planned_at) if last_fu and last_fu.planned_at else None,
                        "last_contacted_at": str(customer.last_contacted_at) if customer.last_contacted_at else None,
                        "active_opportunities": active_opps,
                        "active_quotations": active_quot,
                        "credit_utilization": credit_util,
                        "ar_overdue_days": ar_days,
                        "health_score": h_score,
                        "health_label": h_label,
                    }
                    churn_result = await CustomerAgent.churn_risk(data)

                    insights = customer.ai_insights or {}
                    insights["churn"] = churn_result
                    insights["churn_updated_at"] = datetime.now(timezone.utc).isoformat()
                    customer.ai_insights = insights
                    updated += 1
                except Exception:
                    logger.warning(f"Churn prediction failed for customer {customer.id}")

            await db.commit()
            logger.info(f"Churn prediction complete: {updated}/{len(customers)} customers analyzed")
        except Exception:
            await db.rollback()
            logger.exception("Churn prediction batch failed")


async def run_notification_check():
    """Check and create notifications for deliveries, payments, followups, contracts."""
    from datetime import datetime, timezone, timedelta

    from sqlalchemy import select
    from app.database import async_session
    from app.models.finance import Notification
    from app.models.sales import SalesOrder
    from app.models.customer import CustomerFollowUp, Customer
    from app.models.user import User

    logger.info("Starting notification check")
    now = datetime.now(timezone.utc)
    soon = now + timedelta(days=3)

    async with async_session() as db:
        delivery_orders = []
        overdue_followups = []
        try:
            # Get default user (first admin) as fallback
            default_user = (await db.execute(
                select(User).limit(1)
            )).scalar_one_or_none()
            default_user_id = default_user.id if default_user else 1

            delivery_orders = (await db.execute(
                select(SalesOrder).where(
                    SalesOrder.deleted_at.is_(None),
                    SalesOrder.status == "pending",
                    SalesOrder.delivery_date.isnot(None),
                    SalesOrder.delivery_date <= soon,
                    SalesOrder.delivery_date >= now,
                )
            )).scalars().all()

            for order in delivery_orders:
                target_user_id = default_user_id
                if order.customer_id:
                    cust = (await db.execute(
                        select(Customer.owner).where(Customer.id == order.customer_id)
                    )).scalar_one_or_none()
                    if cust:
                        u = (await db.execute(
                            select(User.id).where(User.username == cust)
                        )).scalar()
                        if u:
                            target_user_id = u

                notif = Notification(
                    user_id=target_user_id, type="delivery", title="交期临近提醒",
                    content=f"订单 {order.order_no} 交货日期临近 ({order.delivery_date.strftime('%Y-%m-%d')})" if order.delivery_date else f"订单 {order.order_no} 交期临近",
                    related_id=order.id,
                )
                db.add(notif)

            overdue_followups = (await db.execute(
                select(CustomerFollowUp).where(
                    CustomerFollowUp.deleted_at.is_(None),
                    CustomerFollowUp.status == "pending",
                    CustomerFollowUp.planned_at.isnot(None),
                    CustomerFollowUp.planned_at < now,
                )
            )).scalars().all()

            for fup in overdue_followups:
                target_user_id = default_user_id
                if fup.assigned_to:
                    u = (await db.execute(
                        select(User.id).where(User.username == fup.assigned_to)
                    )).scalar()
                    if u:
                        target_user_id = u

                notif = Notification(
                    user_id=target_user_id, type="followup", title="跟进待处理提醒",
                    content=f"客户 ID {fup.customer_id} 的跟进任务已逾期",
                    related_id=fup.id,
                )
                db.add(notif)

            await db.commit()
        except Exception:
            await db.rollback()

    logger.info(f"Notification check complete: {len(delivery_orders)} delivery, {len(overdue_followups)} followup")


def start_scheduler():
    scheduler.add_job(run_rfm_batch, "cron", hour=2, minute=0, id="rfm_batch")
    scheduler.add_job(run_churn_prediction, "cron", hour=3, minute=0, id="churn_prediction")
    scheduler.add_job(run_notification_check, "cron", hour=8, minute=0, id="notification_check")
    scheduler.start()
    logger.info("AI job scheduler started")


def stop_scheduler():
    scheduler.shutdown()
