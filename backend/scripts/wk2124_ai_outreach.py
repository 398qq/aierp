"""
给 leads 表里所有 WK2124 lead 写 AI 个性化开场白

每个开场白 100-150 字, 针对该 lead 的行业/公司特点生成, 销售员直接复制粘贴。
"""
import argparse
import asyncio
import sys
import datetime
sys.path.insert(0, "/home/ttdiy/aierp/backend")
from app.models import (  # noqa
    account, approval, audit, customer, document,
    finance, product, rbac, report, sales, transaction, user,
)
from app.database import async_session
from app.models.lead import Lead
from app.models.product import Product
from app.models.base import utc_now
from sqlalchemy import select


# 行业-开场白模板 (按行业定制开场, 然后后缀 + 100字)
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
    "电子制造": "电子制造/PCBA 工厂, 客户项目里多串口场景应该不少。",
    "集成电路": "IC 设计/分销同行, 多半知道 WK2124 这颗国产料。",
    "消费电子": "消费电子里只要有 UART 扩展需求, 都能用上。",
    "电源": "电源/电池管理里 MCU 串口接显示屏/通信模块, 扩 2 路很常见。",
}


def match_hook(lead: Lead) -> str:
    ind = lead.industry or ""
    for k, v in INDUSTRY_HOOKS.items():
        if k in ind:
            return v
    # 老客户交叉销售
    if lead.source == "cross_reference":
        return f"翻了下您的采购记录, 之前买过 {lead.industry} 类的产品, 应该是熟悉 WK 品牌的。"
    return f"看您在 {lead.industry or '电子'} 行业, 应该有 MCU 串口扩展的场景。"


# 通用结尾
COMMON_TAIL = """
我们代理的成都为开微 WK2124-ISSG 是一颗工业级 SPI 转双 UART 芯片, 2.5V~5V 宽压, 2Mbps, 256 字节 FIFO/通道, SSOP-20 封装。
对标 NXP SC16IS752, 宽压更优, 价格低约 30%, 国产供货稳定。
可否寄 5pcs 样片 + 规格书 + Demo Code 试一下?
"""


def make_outreach(lead: Lead) -> str:
    company = lead.short_name or lead.company_name
    if not lead.contact_name:
        salutation = "您好"
    else:
        salutation = f"{lead.contact_name} 您好"

    hook = match_hook(lead)

    # 拼成 100-150 字
    text = f"""{salutation},

{hook}

{COMMON_TAIL.strip()}

{{你的名字}} | {{公司}}
手机: {{手机}}  微信: {{微信号}}"""
    return text.strip()


async def main(dry_run: bool, overwrite: bool):
    async with async_session() as db:
        r = await db.execute(
            select(Lead).where(Lead.product_id == select(Product.id).where(Product.sku == "WK2124-ISSG").scalar_subquery())
        )
        leads = list(r.scalars())
        print(f"找到 {len(leads)} 条 WK2124 lead")

        written = 0
        skipped = 0
        for l in leads:
            if l.ai_outreach and not overwrite:
                skipped += 1
                continue
            outreach = make_outreach(l)
            if dry_run:
                print(f"\n[{l.id}] {l.company_name} ({l.industry})")
                print(f"  fit={l.fit_score} priority={l.priority}")
                print(f"  outreach: {outreach[:120]}...")
            else:
                l.ai_outreach = outreach
                l.ai_outreach_at = utc_now()
                written += 1
                print(f"  [{l.id}] {l.company_name[:30]:32s}  fit={l.fit_score:5.1f}  outreach 写入")
        if not dry_run:
            await db.commit()
            print(f"\n✅ 写入 {written} 条, 跳过 {skipped} 条 (已有)")
        else:
            print(f"\n[Dry-run] 将写 {len(leads) - skipped} 条, 跳过 {skipped} 条")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--overwrite", action="store_true", help="覆盖已有开场白")
    args = ap.parse_args()
    asyncio.run(main(dry_run=args.dry_run, overwrite=args.overwrite))
