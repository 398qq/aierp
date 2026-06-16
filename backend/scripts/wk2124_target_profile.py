"""
WK2124-ISSG 目标客户画像脚本

输入: products 表里的 WK2124-ISSG
输出: 1) 产品定位  2) 目标行业  3) 应用场景  4) 关键词清单  5) 决策建议

不会修改数据库, 纯只读分析。
"""
import asyncio
import sys
from dataclasses import dataclass, field
from typing import Optional

sys.path.insert(0, "/home/ttdiy/aierp/backend")
from app.models import (  # noqa
    account, approval, audit, customer, document,
    finance, product, rbac, report, sales, transaction, user,
)
from app.database import async_session
from app.models.product import Product
from app.models.lead import Lead
from sqlalchemy import select


# ── 产品定位推导 ──
@dataclass
class ProductProfile:
    sku: str
    name: str
    brand: str
    package: str
    specs: str
    function: str            # 核心功能
    interfaces: list[str]    # 接口
    voltage_range: str       # 电压
    speed: str               # 速率
    use_cases: list[str]     # 适用场景
    not_use_cases: list[str] = field(default_factory=list)


def derive_profile(p: Product, brand_name: str) -> ProductProfile:
    specs = (p.specs or "")
    return ProductProfile(
        sku=p.sku,
        name=p.name,
        brand=brand_name,
        package=p.package_type or "N/A",
        specs=specs,
        function="SPI 转 2 路 UART 桥接扩展",   # 来自 specs 推断
        interfaces=["SPI", "UART×2", "FIFO 256B/ch"],
        voltage_range="2.5V~5V 宽压",
        speed="2 Mbps",
        use_cases=[
            # 主 MCU 串口不够用，需要扩出 2 路 UART
            "主控 UART 资源不够, 用 SPI 扩出双串口",
            # 工业 / 仪器仪表常用 UART 接传感器/模块
            "工业仪表/传感器: 串口接 RFID / 扫码枪 / 温压流",
            # 物联网网关需要多串口设备接入
            "IoT 网关/边缘网关: 多路串口接 LoRa/NB-IoT/4G 模块",
            # 充电桩 / 智能电表串口通信
            "充电桩 / 智能电表 / 智能水表 / 智能燃气表",
            # 工控 PLC
            "PLC / 工控板: SPI 主控 + 多串口子模块通信",
            # 路由器 / 交换机 console
            "通信设备 console 调试口扩展",
            # 智能门锁 / 智能家居网关
            "智能门锁 / 智能家居网关串口对接",
            # POS / 收银外设
            "POS / 收银终端外设: 钱箱、客显、扫码",
            # 车载 T-Box
            "车载 T-Box / 车机多路串口接入",
        ],
        not_use_cases=[
            "高速 USB / 以太网场景 (这芯片不提供)",
            "对成本极敏感、单价 < ¥1 的消费小件 (SSOP-20 偏大)",
        ],
    )


# ── 目标行业 + 关键词 ──
TARGET_INDUSTRIES = [
    {
        "industry": "工业自动化",
        "score": 95,
        "reason": "PLC/工控板 SPI 资源通常富余, 但 UART 经常不够, WK2124 是经典方案",
        "keywords": ["PLC", "工控板", "工业网关", "工业控制器", "RS485", "Modbus"],
    },
    {
        "industry": "智能电表/水表/气表",
        "score": 92,
        "reason": "通信模块集中器需多路 UART 接采集/上行模块, SPI 桥接非常匹配",
        "keywords": ["智能电表", "智能水表", "智能燃气表", "集中器", "通信模块", "AMI"],
    },
    {
        "industry": "充电桩 / 充电模块",
        "score": 90,
        "reason": "主控 SPI 扩展多路 UART 接 BMS/读卡器/4G 模块, 行业成熟方案",
        "keywords": ["充电桩", "充电模块", "BMS", "OCPP", "读卡器", "4G 通信"],
    },
    {
        "industry": "IoT 网关 / 边缘计算",
        "score": 88,
        "reason": "需要多路串口接 LoRa/NB-IoT/BLE/4G 子模块, 通用工业级温度",
        "keywords": ["IoT 网关", "边缘网关", "LoRa", "NB-IoT", "4G Cat.1", "工业网关"],
    },
    {
        "industry": "智能家居 / 智能门锁",
        "score": 80,
        "reason": "智能家居主机网关常需扩展串口接 433/Zigbee/蓝牙/语音模块",
        "keywords": ["智能家居网关", "智能门锁", "Zigbee 网关", "Matter 桥接"],
    },
    {
        "industry": "POS / 收银 / 商业显示",
        "score": 78,
        "reason": "POS 主控 UART 接钱箱、客显、电子秤、扫码, 串口需求多",
        "keywords": ["POS", "收银机", "客显", "电子秤", "扫码枪", "钱箱"],
    },
    {
        "industry": "仪器仪表 / 医疗设备",
        "score": 75,
        "reason": "便携仪器多串口接血氧/血压/温度等模块; 工业级稳定性好",
        "keywords": ["便携仪器", "医疗监护", "血氧仪", "分析仪", "数据采集"],
    },
    {
        "industry": "汽车电子 (T-Box / 车机)",
        "score": 70,
        "reason": "T-Box 串口接 GNSS/4G/蓝牙/OBD, WK2124 工业级温度合适",
        "keywords": ["T-Box", "车机", "OBD", "GNSS", "车载网关"],
    },
    {
        "industry": "通信设备 / 路由器",
        "score": 65,
        "reason": "路由器/交换机 console 扩展, 偏小众但稳定需求",
        "keywords": ["路由器", "交换机", "console 扩展", "光猫"],
    },
    {
        "industry": "消费电子 (慎入)",
        "score": 40,
        "reason": "SSOP-20 + 工业级偏大, 消费类一般选更小封装或集成方案",
        "keywords": [],
    },
]


# ── 主流程 ──
async def main():
    async with async_session() as db:
        result = await db.execute(
            select(Product).where(Product.sku == "WK2124-ISSG")
        )
        p = result.scalar_one_or_none()
        if not p:
            print("❌ 没找到 WK2124-ISSG")
            return

        # 拉品牌名 (join brand table)
        brand_name = "WK 成都为开微"
        try:
            from app.models.product import Brand
            r2 = await db.execute(select(Brand).where(Brand.id == p.brand_id))
            b = r2.scalar_one_or_none()
            if b:
                brand_name = b.name
        except Exception:
            pass

        profile = derive_profile(p, brand_name)

        # ── 输出 ──
        print("=" * 70)
        print(" WK2124-ISSG 目标客户画像")
        print("=" * 70)
        print(f"SKU/MPN : {profile.sku}")
        print(f"品牌    : {profile.brand}")
        print(f"封装    : {profile.package}")
        print(f"规格    : {profile.specs}")
        print(f"核心功能: {profile.function}")
        print(f"接口    : {', '.join(profile.interfaces)}")
        print(f"电压    : {profile.voltage_range}")
        print(f"速率    : {profile.speed}")
        print()
        print("─" * 70)
        print(" 适合场景 (Use Cases)")
        print("─" * 70)
        for i, uc in enumerate(profile.use_cases, 1):
            print(f"  {i:2d}. {uc}")
        print()
        print("─" * 70)
        print(" 不适合 / 慎入")
        print("─" * 70)
        for i, uc in enumerate(profile.not_use_cases, 1):
            print(f"  {i:2d}. {uc}")
        print()
        print("─" * 70)
        print(" 目标行业打分 (1-100)")
        print("─" * 70)
        sorted_ind = sorted(TARGET_INDUSTRIES, key=lambda x: -x["score"])
        for ind in sorted_ind:
            bar = "█" * (ind["score"] // 5) + "░" * (20 - ind["score"] // 5)
            print(f"  {ind['score']:3d} {bar}  {ind['industry']}")
            print(f"         理由: {ind['reason']}")
            if ind["keywords"]:
                print(f"         关键词: {', '.join(ind['keywords'])}")
            print()

        # 总关键词汇总 (供后续网搜/客户筛选用)
        all_kw = set()
        for ind in sorted_ind:
            all_kw.update(ind["keywords"])
        print("─" * 70)
        print(" 总关键词池 (供网搜/customer 匹配用)")
        print("─" * 70)
        print(f"  {sorted(all_kw)}")
        print()

        # leads 表当前情况
        r3 = await db.execute(select(Lead).where(Lead.product_id == p.id))
        existing_leads = list(r3.scalars())
        print("─" * 70)
        print(" leads 表现状 (product_id = WK2124-ISSG)")
        print("─" * 70)
        if not existing_leads:
            print("  暂无 lead 记录 (后续 #3/#4 步骤会写入)")
        else:
            print(f"  共 {len(existing_leads)} 条")
            for l in existing_leads[:5]:
                print(f"  - [{l.priority}] {l.company_name} ({l.status}) fit={l.fit_score}")

        # 决策建议
        print()
        print("=" * 70)
        print(" 决策建议")
        print("=" * 70)
        print("""
 1. 优先切入 TOP3 行业 (工业自动化 / 智能表计 / 充电桩), 命中率最高
 2. 关键词用于:
    - #3 步骤: web 搜索"工控板 + UART 扩展"等找公司
    - #4 步骤: 在 337 个客户里按关键词交叉
    - 销售员: 用关键词去搜企查查/天眼查
 3. 慎入消费电子; 慎入需要 USB/以太网的项目
 4. 同类竞品 (客户选型时常对比): XR21V1410 (MaxLinear), SC16IS752 (NXP),
    TL16C752 (TI), WCH CH432 (南京沁恒). 我们的 WK2124-ISSG 在 2.5V-5V
    宽压 + SSOP-20 工业级上是强项
 5. 客户分级建议:
    - fit_score >= 80  -> high (周内触达)
    - 60-80            -> medium (2 周内)
    - < 60             -> low (放 lead 池观察)
        """)

asyncio.run(main())
