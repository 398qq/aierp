"""
网搜候选 lead 入库 (WK2124-ISSG)

把 web 搜索整理出的 TOP 候选公司写入 leads 表, source=web_search。
所有 fit_score/fit_reason 是基于公开信息的估算, 需要销售员后续校准。

用法:
    python scripts/wk2124_seed_leads.py --dry-run   # 只打印
    python scripts/wk2124_seed_leads.py             # 实际插入

不会修改 customers 表, 不会修改 products 表。
"""
import argparse
import asyncio
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
from sqlalchemy import select


# 候选 lead 清单
# fit_score 是估算 (0-100), 后续销售员会校准
# source_detail 记录来源 query, 方便审核
CANDIDATES = [
    # ── 工业自动化 (PLC / 工控板) ──
    {"company_name": "深圳市信捷电气有限公司", "short_name": "信捷", "region": "江苏无锡",
     "industry": "工业自动化", "company_size": "上市",
     "contact_website": "https://www.xinje.com/",
     "fit_score": 90, "fit_reason": "国内中小型 PLC 头部, UART 扩展需求典型",
     "estimated_annual_volume": 50000, "estimated_annual_value": 250000,
     "source_detail": "国内 PLC 厂商清单"},
    {"company_name": "深圳市汇川技术股份有限公司", "short_name": "汇川", "region": "广东深圳",
     "industry": "工业自动化", "company_size": "上市",
     "contact_website": "https://www.inovance.com/",
     "fit_score": 92, "fit_reason": "国内工业自动化龙头, PLC+伺服+变频全产品线",
     "estimated_annual_volume": 80000, "estimated_annual_value": 400000,
     "source_detail": "国内 PLC 厂商清单"},
    {"company_name": "北京和利时集团", "short_name": "和利时", "region": "北京",
     "industry": "工业自动化", "company_size": "大型",
     "contact_website": "https://www.hollysys.com/",
     "fit_score": 88, "fit_reason": "大型 PLC 唯一国产, LM/LK/MC 系列有扩展需求",
     "estimated_annual_volume": 60000, "estimated_annual_value": 300000,
     "source_detail": "国内 PLC 厂商清单"},
    {"company_name": "永宏电机股份有限公司", "short_name": "FATEK 永宏", "region": "台湾",
     "industry": "工业自动化", "company_size": "中型",
     "contact_website": "https://www.fatek.com/",
     "fit_score": 80, "fit_reason": "中小型 PLC 老牌, FATEK 品牌, 串口模块典型用户",
     "estimated_annual_volume": 20000, "estimated_annual_value": 100000,
     "source_detail": "国内 PLC 厂商清单"},
    {"company_name": "深圳市芯橙科技科技有限公司", "short_name": "芯橙科技", "region": "广东深圳",
     "industry": "充电桩", "company_size": "中型",
     "contact_website": "https://www.x-cheng.com/",
     "fit_score": 88, "fit_reason": "充电桩主控板方案商, PCBA 一站式, UART 接 4G/读卡器",
     "estimated_annual_volume": 30000, "estimated_annual_value": 150000,
     "source_detail": "充电桩控制板 厂商清单"},
    {"company_name": "南京捷然电子技术有限公司", "short_name": "捷然电子", "region": "江苏南京",
     "industry": "充电桩", "company_size": "小型",
     "contact_website": "http://www.njjrdz.com/",
     "fit_score": 82, "fit_reason": "充电桩核心控制器方案, 自研 7KW-40KW 主板",
     "estimated_annual_volume": 15000, "estimated_annual_value": 75000,
     "source_detail": "充电桩控制板 厂商清单"},
    {"company_name": "宜宾丰川动力科技有限公司", "short_name": "丰川动力", "region": "四川宜宾",
     "industry": "充电桩", "company_size": "小型",
     "contact_website": "http://www.fengchuanpower.com/",
     "fit_score": 80, "fit_reason": "国标充电桩控制器 FC4512, RT-Thread 系统",
     "estimated_annual_volume": 10000, "estimated_annual_value": 50000,
     "source_detail": "充电桩控制板 厂商清单"},
    {"company_name": "广州宇脉电子科技有限公司", "short_name": "宇脉电子", "region": "广东广州",
     "industry": "充电桩", "company_size": "小型",
     "contact_website": "http://www.gdymdz.com/",
     "fit_score": 78, "fit_reason": "自助充电桩主控板方案",
     "estimated_annual_volume": 10000, "estimated_annual_value": 50000,
     "source_detail": "充电桩控制板 厂商清单"},
    {"company_name": "福州耐特电子科技有限公司", "short_name": "耐特电子", "region": "福建福州",
     "industry": "工业自动化", "company_size": "小型",
     "contact_website": "",
     "fit_score": 75, "fit_reason": "PLC 工控板生产商, 多行业适配",
     "estimated_annual_volume": 8000, "estimated_annual_value": 40000,
     "source_detail": "PLC 工控板 厂商清单"},
    {"company_name": "泉州市誉达电子科技有限公司", "short_name": "誉达电子", "region": "福建泉州",
     "industry": "工业自动化", "company_size": "小型",
     "contact_website": "http://www.ydplc.com/",
     "fit_score": 75, "fit_reason": "国产 PLC YDA3u 系列, 兼容三菱, 模块化设计",
     "estimated_annual_volume": 8000, "estimated_annual_value": 40000,
     "source_detail": "PLC 工控板 厂商清单"},

    # ── 智能电表 / 集中器 ──
    {"company_name": "成都长城开发科技有限公司", "short_name": "KAIFA 长城开发", "region": "四川成都",
     "industry": "智能电表", "company_size": "中型",
     "contact_website": "https://www.kaifa.cn/",
     "fit_score": 92, "fit_reason": "深科技控股, AMI 智能计量系统方案商, 多串口模块",
     "estimated_annual_volume": 100000, "estimated_annual_value": 500000,
     "source_detail": "智能电表 集中器 厂商清单"},
    {"company_name": "安科瑞电气股份有限公司", "short_name": "安科瑞", "region": "上海",
     "industry": "智能电表", "company_size": "上市",
     "contact_website": "https://www.acrel.cn/",
     "fit_score": 90, "fit_reason": "创业板 300286, 智能电表/集中器/电力监控全栈",
     "estimated_annual_volume": 80000, "estimated_annual_value": 400000,
     "source_detail": "智能电表 集中器 厂商清单"},
    {"company_name": "宁波三星电气股份有限公司", "short_name": "三星医疗/三星电气", "region": "浙江宁波",
     "industry": "智能电表", "company_size": "上市",
     "contact_website": "",
     "fit_score": 85, "fit_reason": "电能计量/信息采集, 智能电表+用电管理终端",
     "estimated_annual_volume": 60000, "estimated_annual_value": 300000,
     "source_detail": "国内十大智能电表"},
    {"company_name": "江苏林洋能源股份有限公司", "short_name": "林洋", "region": "江苏南通",
     "industry": "智能电表", "company_size": "上市",
     "contact_website": "https://www.linyang.com/",
     "fit_score": 85, "fit_reason": "电子式电能表头部, 智能电表+AMI",
     "estimated_annual_volume": 50000, "estimated_annual_value": 250000,
     "source_detail": "国内十大智能电表"},
    {"company_name": "威胜信息技术股份有限公司", "short_name": "威胜信息", "region": "湖南长沙",
     "industry": "智能电表", "company_size": "上市",
     "contact_website": "https://www.wasion.com/",
     "fit_score": 88, "fit_reason": "智能电表/集中器/通信模块全方案",
     "estimated_annual_volume": 70000, "estimated_annual_value": 350000,
     "source_detail": "智能电表 集中器 厂商清单"},
    {"company_name": "湖南华烨智能通信技术股份有限公司", "short_name": "华烨智能", "region": "湖南",
     "industry": "智能电表", "company_size": "中型",
     "contact_website": "http://www.hyearcomm.com/",
     "fit_score": 82, "fit_reason": "集中器本地微功率无线模块, 国网/南网规范",
     "estimated_annual_volume": 30000, "estimated_annual_value": 150000,
     "source_detail": "智能电表 集中器 厂商清单"},

    # ── IoT 工业网关 ──
    {"company_name": "上海泗博自动化技术有限公司", "short_name": "Sibotech 泗博", "region": "上海",
     "industry": "IoT 工业网关", "company_size": "中型",
     "contact_website": "http://www.sibotech.net/",
     "fit_score": 90, "fit_reason": "Modbus/NB-IoT 网关专业厂家, 串口服务器典型用户",
     "estimated_annual_volume": 50000, "estimated_annual_value": 250000,
     "source_detail": "IoT 工业网关 厂商清单"},
    {"company_name": "厦门计讯物联科技有限公司", "short_name": "计讯物联", "region": "福建厦门",
     "industry": "IoT 工业网关", "company_size": "中型",
     "contact_website": "https://www.top-iot.com/",
     "fit_score": 88, "fit_reason": "5G/4G/NB-IoT/LoRa 工业网关, 多协议支持",
     "estimated_annual_volume": 40000, "estimated_annual_value": 200000,
     "source_detail": "IoT 工业网关 厂商清单"},
    {"company_name": "研华科技(中国)有限公司", "short_name": "研华 Advantech", "region": "上海",
     "industry": "IoT 工业网关", "company_size": "上市",
     "contact_website": "https://www.advantech.com.cn/",
     "fit_score": 85, "fit_reason": "工业物联网老牌, UNO/EKI 网关有 UART 扩展需求",
     "estimated_annual_volume": 30000, "estimated_annual_value": 150000,
     "source_detail": "工业网关 厂商清单"},
    {"company_name": "摩莎科技(上海)有限公司", "short_name": "MOXA 摩莎", "region": "上海",
     "industry": "IoT 工业网关", "company_size": "上市",
     "contact_website": "https://www.moxa.com.cn/",
     "fit_score": 85, "fit_reason": "串口服务器/网关全球头部, 多串口方案",
     "estimated_annual_volume": 30000, "estimated_annual_value": 150000,
     "source_detail": "工业网关 厂商清单"},
]


def priority_from_score(s: float) -> str:
    if s >= 80:
        return "high"
    if s >= 60:
        return "medium"
    return "low"


async def main(dry_run: bool):
    async with async_session() as db:
        r = await db.execute(select(Product).where(Product.sku == "WK2124-ISSG"))
        p = r.scalar_one_or_none()
        if not p:
            print("❌ 没找到 WK2124-ISSG")
            return
        product_id = p.id

        # 查重: 已有同 company_name + product_id 的不入
        existing = await db.execute(
            select(Lead).where(Lead.product_id == product_id)
        )
        existing_names = {l.company_name for l in existing.scalars()}
        print(f"已存在的 leads: {len(existing_names)} 条")

        inserted = 0
        skipped = 0
        for c in CANDIDATES:
            if c["company_name"] in existing_names:
                skipped += 1
                continue
            lead = Lead(
                product_id=product_id,
                company_name=c["company_name"],
                short_name=c.get("short_name"),
                website=c.get("contact_website") or None,
                industry=c.get("industry"),
                region=c.get("region"),
                company_size=c.get("company_size"),
                source="web_search",
                source_detail=f"web_search: {c.get('source_detail','')}",
                status="new",
                priority=priority_from_score(c["fit_score"]),
                fit_score=c["fit_score"],
                fit_reason=c["fit_reason"],
                estimated_annual_volume=c.get("estimated_annual_volume"),
                estimated_annual_value=c.get("estimated_annual_value"),
                notes="由 wk2124_seed_leads.py 写入; fit_score 是基于公开信息的估算, 销售员校准",
                updated_at=utc_now(),
            )
            if dry_run:
                print(f"  [DRY] {lead.priority:6s} {lead.fit_score:5.1f}  {lead.company_name}  ({lead.industry}, {lead.region})")
            else:
                db.add(lead)
                inserted += 1
                print(f"  [OK ] {lead.priority:6s} {lead.fit_score:5.1f}  {lead.company_name}")
        if not dry_run:
            await db.commit()
            print(f"\n✅ 写入 {inserted} 条, 跳过 {skipped} 条重复")
        else:
            print(f"\n[Dry-run] 计划写入 {len(CANDIDATES) - skipped} 条, 跳过 {skipped} 条重复")

        # 显示按行业聚合
        from collections import Counter
        cnt = Counter(c["industry"] for c in CANDIDATES if c["company_name"] not in existing_names)
        print("\n按行业分布:")
        for ind, n in cnt.most_common():
            print(f"  {ind:25s} {n}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="只打印不入库")
    args = ap.parse_args()
    asyncio.run(main(dry_run=args.dry_run))
