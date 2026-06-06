"""Customer AI vocabulary — bounded enums and finite sets.

These replace the loose module-level sets in the legacy
`app.api.v1.ai.customer_ai` module so that downstream code (form choices,
Pydantic validators, DB CHECK constraints) can share a single source of
truth.
"""
from __future__ import annotations

from enum import Enum


class FollowUpMethod(str, Enum):
    phone = "phone"
    visit = "visit"
    video = "video"
    email = "email"
    wechat = "wechat"
    other = "other"


class FollowUpStatus(str, Enum):
    planned = "planned"
    in_progress = "in_progress"
    completed = "completed"
    cancelled = "cancelled"


class FollowUpPriority(str, Enum):
    high = "high"
    medium = "medium"
    low = "low"


class CustomerType(str, Enum):
    terminal = "终端"
    trader = "贸易商"
    solutions = "方案商"
    oem = "OEM"


class CustomerIndustry(str, Enum):
    automotive_electronics = "汽车电子"
    consumer_electronics = "消费电子"
    industrial_control = "工业控制"
    telecom_equipment = "通信设备"
    medical_devices = "医疗器械"
    security_surveillance = "安防监控"
    other = "其他"


class CustomerLevel(str, Enum):
    a = "A"
    b = "B"
    c = "C"
    d = "D"


class CustomerRegion(str, Enum):
    east_china = "华东"
    south_china = "华南"
    north_china = "华北"
    central_china = "华中"
    southwest = "西南"
    northwest = "西北"
    northeast = "东北"
    overseas = "海外"


class CustomerSource(str, Enum):
    exhibition = "展会"
    referral = "转介绍"
    online_marketing = "线上推广"
    cold_call = "电话开发"
    internal_resource = "公司资源"


# Frozen value sets (string-valued) for cheap `in` checks
FOLLOWUP_METHOD_VALUES: frozenset[str] = frozenset(m.value for m in FollowUpMethod)
FOLLOWUP_STATUS_VALUES: frozenset[str] = frozenset(m.value for m in FollowUpStatus)
FOLLOWUP_PRIORITY_VALUES: frozenset[str] = frozenset(m.value for m in FollowUpPriority)
CUSTOMER_TYPE_VALUES: frozenset[str] = frozenset(m.value for m in CustomerType)
CUSTOMER_INDUSTRY_VALUES: frozenset[str] = frozenset(m.value for m in CustomerIndustry)
CUSTOMER_LEVEL_VALUES: frozenset[str] = frozenset(m.value for m in CustomerLevel)
CUSTOMER_REGION_VALUES: frozenset[str] = frozenset(m.value for m in CustomerRegion)
CUSTOMER_SOURCE_VALUES: frozenset[str] = frozenset(m.value for m in CustomerSource)


__all__ = [
    "FollowUpMethod",
    "FollowUpStatus",
    "FollowUpPriority",
    "CustomerType",
    "CustomerIndustry",
    "CustomerLevel",
    "CustomerRegion",
    "CustomerSource",
    "FOLLOWUP_METHOD_VALUES",
    "FOLLOWUP_STATUS_VALUES",
    "FOLLOWUP_PRIORITY_VALUES",
    "CUSTOMER_TYPE_VALUES",
    "CUSTOMER_INDUSTRY_VALUES",
    "CUSTOMER_LEVEL_VALUES",
    "CUSTOMER_REGION_VALUES",
    "CUSTOMER_SOURCE_VALUES",
]
