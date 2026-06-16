"""
现有 337 客户交叉分析 — 找出"和 WK2124-ISSG 匹配但还没成交过"的客户
纯只读, 不写库。
"""
import asyncio
import sys
from collections import Counter
sys.path.insert(0, "/home/ttdiy/aierp/backend")
from app.models import (  # noqa
    account, approval, audit, customer, document,
    finance, product, rbac, report, sales, transaction, user,
)
from app.database import async_session
from app.models.customer import Customer
from app.models.product import Product
from sqlalchemy import select, func, or_, and_, exists


# WK2124 匹配的关键词
INDUSTRY_KW = [
    "电子", "芯片", "半导体", "IC", "元器件",
    "智能", "物联网", "IoT", "工控", "自动化",
    "通信", "仪器", "仪表", "嵌入式", "电表",
    "充电", "PLC", "网关", "模块", "控制",
]


async def main():
    async with async_session() as db:
        # 1. 找 WK2124-ISSG
        r = await db.execute(select(Product).where(Product.sku == "WK2124-ISSG"))
        wk2124 = r.scalar_one_or_none()
        if not wk2124:
            print("❌ 没找到 WK2124-ISSG")
            return
        print(f"WK2124 product_id = {wk2124.id}\n")

        # 2. 总客户数
        total = await db.scalar(select(func.count(Customer.id)))
        print(f"现有客户总数: {total}\n")

        # 3. 行业分布
        r = await db.execute(
            select(Customer.industry, func.count(Customer.id))
            .group_by(Customer.industry)
            .order_by(func.count(Customer.id).desc())
        )
        print("── 行业分布 (前 20) ──")
        for ind, cnt in r:
            if ind:
                print(f"  {ind:20s} {cnt}")

        # 4. 找"行业包含关键词"的客户
        industry_filters = [Customer.industry.ilike(f"%{kw}%") for kw in INDUSTRY_KW]
        r = await db.execute(
            select(Customer)
            .where(or_(*industry_filters))
            .order_by(Customer.industry, Customer.name)
        )
        industry_matches = list(r.scalars())
        print(f"\n── 行业关键词命中: {len(industry_matches)} 家客户 ──")
        # 去重 (or_ 多个 kw 可能重复)
        seen = set()
        uniq = []
        for c in industry_matches:
            if c.id in seen:
                continue
            seen.add(c.id)
            uniq.append(c)
        print(f"  去重后: {len(uniq)} 家\n")

        # 5. 排除"已成交过 WK2124"的客户
        from app.models.sales import SalesOrder, SalesOrderItem
        already_bought_subq = (
            select(SalesOrder.customer_id)
            .join(SalesOrderItem, SalesOrderItem.order_id == SalesOrder.id)
            .where(SalesOrderItem.product_id == wk2124.id)
            .distinct()
        )
        r = await db.execute(
            select(Customer)
            .where(
                Customer.id.in_([c.id for c in uniq]),
                ~Customer.id.in_(already_bought_subq)
            )
        )
        candidates = list(r.scalars())
        already_bought = len(uniq) - len(candidates)
        print(f"── 已成交过 WK2124 的客户: {already_bought} 家 (排除) ──")
        print(f"── 候选清单 (行业匹配 + 未成交 WK2124): {len(candidates)} 家 ──\n")

        # 6. 进一步: 客户买过其他 IC/芯片/电子元件 类产品
        # 这里用 products.category 简单判断
        candidate_ids = [c.id for c in candidates]
        # 查 candidate 们买过的所有 products
        r = await db.execute(
            select(SalesOrder.customer_id, Product.id, Product.sku, Product.name, Product.category)
            .join(SalesOrderItem, SalesOrderItem.order_id == SalesOrder.id)
            .join(Product, Product.id == SalesOrderItem.product_id)
            .where(SalesOrder.customer_id.in_(candidate_ids))
        )
        bought_rows = r.all()

        # 客户-产品分类映射
        cust_bought_categories = {}  # customer_id -> set(category)
        cust_chip_count = {}  # customer_id -> count
        for cust_id, pid, sku, name, cat in bought_rows:
            cust_bought_categories.setdefault(cust_id, set()).add(cat or "未知")
            cat_l = (cat or "").lower()
            sku_l = (sku or "").lower()
            name_l = (name or "").lower()
            is_chip = any(kw in (cat_l + sku_l + name_l) for kw in [
                "ic", "芯片", "半导体", "chip", "mcu", "接口", "桥接",
                "uart", "spi", "232", "485", "模块",
            ])
            if is_chip:
                cust_chip_count[cust_id] = cust_chip_count.get(cust_id, 0) + 1

        # 7. 按行业聚合 + 排序输出
        candidates.sort(key=lambda c: (-cust_chip_count.get(c.id, 0), c.name))
        print("─" * 78)
        print(f"{'rank':4s} {'客户名':32s} {'行业':12s} {'地区':8s} {'状态':10s} {'芯片历史':>8s}")
        print("─" * 78)
        for i, c in enumerate(candidates, 1):
            chip_n = cust_chip_count.get(c.id, 0)
            print(f"{i:4d} {c.name[:30]:32s} {(c.industry or '?')[:10]:12s} "
                  f"{(c.region or '?')[:6]:8s} {(c.status or '?'):10s} {chip_n:>8d}")
        print("─" * 78)
        print(f"共 {len(candidates)} 家, 其中有芯片采购历史的 {len(cust_chip_count)} 家")

        # 8. 输出可写回 leads 的脚本建议
        print("\n" + "=" * 78)
        print(" 写入 leads 表建议 (cross_reference 来源)")
        print("=" * 78)
        # 选 top 30 + 芯片历史 >= 1 的
        top = [c for c in candidates if cust_chip_count.get(c.id, 0) >= 1][:30]
        # 打 fit_score
        def fit_for(c, chip_n):
            base = 70
            if chip_n >= 5: base += 20
            elif chip_n >= 2: base += 12
            elif chip_n >= 1: base += 6
            ind = (c.industry or "").lower()
            if any(kw in ind for kw in ["芯片", "ic", "半导体", "电子"]):
                base += 8
            if any(kw in ind for kw in ["工控", "plc", "物联网", "iot", "智能"]):
                base += 4
            return min(base, 95)

        for c in top[:15]:
            chip_n = cust_chip_count.get(c.id, 0)
            score = fit_for(c, chip_n)
            print(f"  {c.name[:30]:32s}  fit={score}  芯片历史={chip_n}  行业={c.industry}")
        print(f"\n  (共 {len(top)} 家建议入 lead 池, source=cross_reference)")

asyncio.run(main())
