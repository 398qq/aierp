"""
WK2124 日扫 lead 入库 + AI 开场白

从 stdin 或 candidates.json 读候选公司, 去重入 leads, 写 AI 开场白,
输出"今日 TOP N 待触达"报告。

candidates.json 格式:
[
  {
    "company_name": "xxx",
    "short_name": "xxx",        # 可选
    "website": "https://...",    # 可选
    "industry": "工业自动化",     # 可选, 没填就 None
    "region": "广东深圳",         # 可选
    "company_size": "上市",       # 可选
    "fit_score": 85,              # 可选, 没填就 70
    "fit_reason": "...",          # 可选
    "estimated_annual_volume": 50000,  # 可选
    "estimated_annual_value": 250000,  # 可选
    "source": "web_search",       # web_search/cross_reference/referral/manual
    "source_detail": "...",       # 可选
  },
  ...
]

用法:
  # 1. 从 stdin (适合 cron / pipeline)
  echo '[{"company_name":"...","industry":"..."}]' | python wk2124_lead_import.py

  # 2. 从 JSON 文件
  python wk2124_lead_import.py --input .leads_candidates.json

  # 3. dry-run (只打印不入库)
  python wk2124_lead_import.py --dry-run
"""
import argparse
import asyncio
import json
import sys
from typing import Optional

sys.path.insert(0, "/home/ttdiy/aierp/backend")
from app.models import (  # noqa
    account, approval, audit, customer, document,
    finance, product, rbac, report, sales, transaction, user,
)
from app.database import async_session
from app.models.lead import Lead
from app.models.product import Product
from app.models.base import utc_now
from sqlalchemy import select, func
from datetime import datetime, timezone


def priority_from_score(s: float) -> str:
    if s >= 80: return "high"
    if s >= 60: return "medium"
    return "low"


# 行业钩子 (复用 wk2124_ai_outreach.py 的逻辑)
INDUSTRY_HOOKS = {
    "工业自动化": "您是 PLC/工控板领域的老兵了, 选型上对接口芯片应该不陌生。",
    "智能电表": "智能电表/集中器行业最近在推 4G Cat.1 / NB-IoT 通信模组, 主控 UART 不够是常见痛点。",
    "充电桩": "现在充电桩主控板 BOM 成本压力大, 4G 通信 + 读卡器 + BMS 三选二又常常挤爆 UART。",
    "IoT 工业网关": "工业网关/边缘网关要接 LoRa/NB-IoT/4G 多路设备, 一颗芯片扩出双串口是老问题了。",
    "智能家居": "智能家居网关要接 Zigbee/433/蓝牙子模块, UART 经常不够。",
    "POS": "POS 收银主板 UART 接钱箱、客显、扫码枪, 串口资源紧张。",
    "汽车电子": "T-Box / 车机串口接 GNSS/4G/蓝牙/OBD, 工业级温度是刚需。",
    "工控机": "工控机/工业电脑, 多串口是基础需求, 传统 NXP/TI 方案偏贵。",
    "方案公司": "方案公司接不同项目, BOM 里 UART 扩展芯片反复选型, 一颗能通用就最好。",
    "电子元器件分销": "电子元器件分销商朋友们, 串口扩展这一类长期有量, 不知道有没有兴趣备一颗。",
    "集成电路": "IC 设计/分销同行, 多半知道 WK2124 这颗国产料。",
    "电源": "电源/电池管理里 MCU 串口接显示屏/通信模块, 扩 2 路很常见。",
}
COMMON_TAIL = """我们代理的成都为开微 WK2124-ISSG 是一颗工业级 SPI 转双 UART 芯片, 2.5V~5V 宽压, 2Mbps, 256 字节 FIFO/通道, SSOP-20 封装。
对标 NXP SC16IS752, 宽压更优, 价格低约 30%, 国产供货稳定。
可否寄 5pcs 样片 + 规格书 + Demo Code 试一下?"""


def make_outreach(c: dict) -> str:
    salutation = f"{c.get('contact_name', '')} 您好" if c.get("contact_name") else "您好"
    ind = c.get("industry", "")
    hook = next((v for k, v in INDUSTRY_HOOKS.items() if k in ind),
                f"看您在 {ind or '电子'} 行业, 应该有 MCU 串口扩展的场景。")
    return f"""{salutation},

{hook}

{COMMON_TAIL}

{{你的名字}} | {{公司}}
手机: {{手机}}  微信: {{微信号}}"""


async def run_import(candidates: list, dry_run: bool):
    if not candidates:
        print("⚠️  没有候选公司, 跳过")
        return

    async with async_session() as db:
        r = await db.execute(select(Product).where(Product.sku == "WK2124-ISSG"))
        p = r.scalar_one_or_none()
        if not p:
            print("❌ 没找到 WK2124-ISSG")
            return
        product_id = p.id

        # 查重
        r = await db.execute(select(Lead).where(Lead.product_id == product_id))
        existing = {l.company_name for l in r.scalars()}
        print(f"已存在 leads: {len(existing)} 条")

        inserted = 0
        skipped = 0
        for c in candidates:
            cn = c.get("company_name", "").strip()
            if not cn:
                continue
            if cn in existing:
                skipped += 1
                print(f"  [SKIP] {cn} (已存在)")
                continue
            score = c.get("fit_score", 70)
            lead = Lead(
                product_id=product_id,
                company_name=cn,
                short_name=c.get("short_name"),
                website=c.get("website"),
                industry=c.get("industry"),
                region=c.get("region"),
                company_size=c.get("company_size"),
                source=c.get("source", "web_search"),
                source_detail=c.get("source_detail"),
                status="new",
                priority=priority_from_score(score),
                fit_score=score,
                fit_reason=c.get("fit_reason"),
                estimated_annual_volume=c.get("estimated_annual_volume"),
                estimated_annual_value=c.get("estimated_annual_value"),
                ai_outreach=make_outreach(c),
                ai_outreach_at=utc_now(),
                updated_at=utc_now(),
                notes=f"由 wk2124_lead_import.py 写入 @ {utc_now().isoformat()[:19]}",
            )
            if dry_run:
                print(f"  [DRY] {lead.priority:6s} {lead.fit_score:5.1f}  {lead.company_name}  ({lead.industry})")
            else:
                db.add(lead)
                inserted += 1
                print(f"  [OK ] {lead.priority:6s} {lead.fit_score:5.1f}  {lead.company_name}")

        if not dry_run:
            await db.commit()

        # TOP 5 待触达 (status=new, priority=high, fit_score desc, 没联系过)
        print("\n" + "=" * 70)
        print(" 今日 TOP 待触达 (status=new, 未联系过, 按 fit_score 排序)")
        print("=" * 70)
        r = await db.execute(
            select(Lead)
            .where(
                Lead.product_id == product_id,
                Lead.status == "new",
                Lead.last_contacted_at.is_(None),
            )
            .order_by(Lead.fit_score.desc().nulls_last())
            .limit(5)
        )
        top = list(r.scalars())
        for i, l in enumerate(top, 1):
            print(f"\n  #{i}  {l.company_name}  ({l.priority}, fit={l.fit_score})")
            print(f"      行业: {l.industry}  地区: {l.region}")
            if l.ai_outreach:
                # 截前 200 字
                snippet = l.ai_outreach.replace("\n", " ").strip()[:200]
                print(f"      开场白: {snippet}...")

        # 统计
        r = await db.execute(
            select(Lead.priority, func.count(Lead.id))
            .where(Lead.product_id == product_id)
            .group_by(Lead.priority)
        )
        print("\n" + "=" * 70)
        print(" leads 总览")
        print("=" * 70)
        total = 0
        for pri, n in r:
            print(f"  {pri:8s} {n}")
            total += n
        print(f"  合计     {total}")

        if dry_run:
            print(f"\n[Dry-run] 计划写入 {inserted} 条, 跳过 {skipped} 条")
        else:
            print(f"\n✅ 写入 {inserted} 条, 跳过 {skipped} 条")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", help="candidates JSON 文件路径")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if args.input:
        with open(args.input, "r", encoding="utf-8") as f:
            candidates = json.load(f)
    elif not sys.stdin.isatty():
        candidates = json.loads(sys.stdin.read())
    else:
        # 没有输入, 找默认 candidates.json
        default_path = "/home/ttdiy/aierp/backend/scripts/.leads_candidates.json"
        try:
            with open(default_path, "r", encoding="utf-8") as f:
                candidates = json.load(f)
            print(f"读取 {default_path}")
        except FileNotFoundError:
            print(f"❌ 没指定 --input, stdin 空, 且 {default_path} 不存在")
            print("用法: echo '[{...}]' | python wk2124_lead_import.py")
            print("或:  python wk2124_lead_import.py --input .leads_candidates.json")
            sys.exit(1)

    asyncio.run(run_import(candidates, dry_run=args.dry_run))


if __name__ == "__main__":
    main()
