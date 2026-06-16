"""Cross-ref: 找买过芯片/IC 类的现有客户 (高潜力)"""
import logging
logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
logging.disable(logging.CRITICAL)

import asyncio
import sys
sys.path.insert(0, "/home/ttdiy/aierp/backend")
from app.models import (  # noqa
    account, approval, audit, customer, document,
    finance, product, rbac, report, sales, transaction, user,
)
from app.database import async_session
from app.models.customer import Customer
from app.models.product import Product
from app.models.lead import Lead
from app.models.sales import SalesOrder, SalesOrderItem
from app.models.base import utc_now
from sqlalchemy import select, func, or_, distinct


CHIP_KW = [
    "IC", "芯片", "半导体", "chip", "MCU", "单片机",
    "接口", "桥接", "扩展", "UART", "SPI", "I2C", "232", "485", "485",
    "收发器", "电平转换", "逻辑", "门电路", "运放", "比较器", "稳压",
    "DC-DC", "LDO", "MOS", "二极管", "三极管",
    "模块", "通信", "传感", "FLASH", "EEPROM", "SRAM",
]

INDUSTRY_KW = [
    "电子", "芯片", "半导体", "IC", "元器件",
    "智能", "物联网", "IoT", "工控", "自动化",
    "通信", "仪器", "仪表", "嵌入式", "电表",
    "充电", "PLC", "网关", "模块", "控制",
]


async def main():
    async with async_session() as db:
        r = await db.execute(select(Product).where(Product.sku == "WK2124-ISSG"))
        p = r.scalar_one()
        product_id = p.id

        # 1. 找买过 chip 相关产品的 customer_id 集合
        chip_filters = []
        for col in ("sku", "mpn", "name", "category", "specs", "notes"):
            for kw in CHIP_KW:
                chip_filters.append(getattr(Product, col).ilike(f"%{kw}%"))
        r = await db.execute(
            select(distinct(SalesOrder.customer_id))
            .join(SalesOrderItem, SalesOrderItem.order_id == SalesOrder.id)
            .join(Product, Product.id == SalesOrderItem.product_id)
            .where(or_(*chip_filters))
        )
        chip_buyers = {row[0] for row in r}
        print(f"买过芯片/IC 类产品的客户 (去重): {len(chip_buyers)} 家")

        # 2. 行业关键词命中
        industry_filters = [Customer.industry.ilike(f"%{kw}%") for kw in INDUSTRY_KW]
        r = await db.execute(
            select(Customer).where(or_(*industry_filters))
        )
        industry_matches = list(r.scalars())
        print(f"行业关键词命中: {len(industry_matches)} 家 (未去重)")

        # 3. 取 chip_buyers ∩ industry_matches
        candidates = [c for c in industry_matches if c.id in chip_buyers]
        print(f"∩ 交集: {len(candidates)} 家\n")

        # 4. 排除已成交 WK2124
        already_subq = (
            select(SalesOrder.customer_id)
            .join(SalesOrderItem, SalesOrderItem.order_id == SalesOrder.id)
            .where(SalesOrderItem.product_id == product_id)
            .distinct()
        )
        r = await db.execute(
            select(Customer)
            .where(Customer.id.in_([c.id for c in candidates]))
            .where(~Customer.id.in_(already_subq))
        )
        candidates = list(r.scalars())
        print(f"已成交 WK2124 的: 0 家 (这个产品目前没客户成交过)")
        print(f"最终候选: {len(candidates)} 家\n")

        # 5. 按"芯片历史订单数"排序
        r = await db.execute(
            select(
                SalesOrder.customer_id,
                func.count(SalesOrderItem.id).label("chip_orders"),
                func.sum(SalesOrderItem.quantity * SalesOrderItem.unit_price).label("chip_value")
            )
            .join(SalesOrderItem, SalesOrderItem.order_id == SalesOrder.id)
            .join(Product, Product.id == SalesOrderItem.product_id)
            .where(or_(*chip_filters))
            .group_by(SalesOrder.customer_id)
        )
        chip_stats = {row.customer_id: (row.chip_orders, float(row.chip_value or 0)) for row in r}

        candidates.sort(key=lambda c: (-(chip_stats.get(c.id, (0, 0))[0]), c.name))

        print("─" * 110)
        print(f"{'#':3s} {'客户名':32s} {'行业':18s} {'地区':10s} {'状态':10s} {'芯片订单':>8s} {'芯片金额':>12s}")
        print("─" * 110)
        for i, c in enumerate(candidates, 1):
            n, v = chip_stats.get(c.id, (0, 0))
            print(f"{i:3d} {c.name[:30]:32s} {(c.industry or '?')[:16]:18s} "
                  f"{(c.region or '?')[:8]:10s} {(c.status or '?'):10s} {n:>8d} {v:>12,.0f}")
        print("─" * 110)
        print(f"共 {len(candidates)} 家\n")

        # 6. 写到 leads 表
        if not candidates:
            print("无候选, 不写库")
            return

        # 查重: 已有 leads 跳过
        r = await db.execute(select(Lead).where(Lead.product_id == product_id))
        existing = {l.company_name for l in r.scalars()}
        print(f"已存在 leads: {len(existing)} 条")

        # 写 top 30, fit_score 跟芯片订单数相关
        inserted = 0
        for c in candidates[:30]:
            if c.name in existing:
                continue
            n, v = chip_stats.get(c.id, (0, 0))
            # fit_score: base 70 + 芯片订单
            fit = min(70 + min(n, 15) * 1.5, 95)
            ind_l = (c.industry or "").lower()
            if any(kw in ind_l for kw in ["芯片", "ic", "半导体", "电子"]):
                fit = min(fit + 4, 95)
            priority = "high" if fit >= 80 else "medium"

            lead = Lead(
                product_id=product_id,
                company_name=c.name,
                short_name=c.short_name,
                website=c.website,
                industry=c.industry,
                region=c.region,
                company_size=c.level,  # use level (A/B/C) as company_size proxy
                contact_name=c.contact_person,
                contact_phone=c.phone,
                contact_email=c.email,
                source="cross_reference",
                source_detail=f"cross_reference: 买过 {n} 单芯片类, 总额¥{v:,.0f}",
                status="new",
                priority=priority,
                fit_score=fit,
                fit_reason=f"现有客户, 行业匹配, 芯片采购历史 {n} 单 / ¥{v:,.0f}",
                estimated_annual_volume=max(n * 1000, 1000),
                estimated_annual_value=max(v * 0.1, 5000),
                notes=f"由 wk2124_seed_cross.py 写入; 客户id={c.id}",
                updated_at=utc_now(),
            )
            db.add(lead)
            inserted += 1
            print(f"  [+] {priority:6s} {fit:5.1f}  {c.name}  (芯片历史 {n} 单)")
        await db.commit()
        print(f"\n✅ 写入 {inserted} 条 cross_reference leads")

asyncio.run(main())
