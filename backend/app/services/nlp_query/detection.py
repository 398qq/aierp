"""Domain detection for natural-language ERP queries.

Pure-Python keyword matching. No I/O. The trigger layer (the API
caller) hands off a free-text query, and this module classifies it
into 0+ ERP domains (customers / products / sales / inventory /
finance / suppliers).

Keeping detection isolated from context-building means a new
domain can be added in 1 place: append to DOMAIN_PATTERNS.
"""

from __future__ import annotations

DOMAIN_PATTERNS: list[tuple[str, list[str]]] = [
    (
        "customers",
        [
            "客户",
            "customer",
            "流失",
            "churn",
            "跟进",
            "followup",
            "信用",
            "credit",
            "等级",
            "level",
            "联系人",
            "contact",
        ],
    ),
    (
        "products",
        [
            "产品",
            "product",
            "型号",
            "part",
            "sku",
            "品牌",
            "brand",
            "分类",
            "品类",
            "category",
            "封装",
            "package",
        ],
    ),
    (
        "sales",
        [
            "销售",
            "sale",
            "订单",
            "order",
            "商机",
            "opportunity",
            "报价",
            "quotation",
            "收入",
            "revenue",
            "金额",
            "amount",
            "交付",
            "delivery",
        ],
    ),
    (
        "inventory",
        [
            "库存",
            "inventory",
            "stock",
            "采购",
            "purchase",
            "po",
            "短缺",
            "shortage",
            "滞销",
            "slow",
            "周转",
            "turnover",
            "仓库",
            "warehouse",
        ],
    ),
    (
        "finance",
        [
            "财务",
            "finance",
            "应收",
            "ar",
            "应付",
            "ap",
            "付款",
            "payment",
            "发票",
            "invoice",
            "回款",
            "欠款",
            "dso",
            "现金",
            "cash",
            "对账",
            "reconciliation",
        ],
    ),
    (
        "suppliers",
        ["供应商", "supplier", "交期", "lead time", "供货", "采购单", "purchase order"],
    ),
]


def detect_domains(query: str) -> list[str]:
    """Return domain names mentioned in the query, ordered by keyword hit
    count (most hits first, alphabetical tiebreaker)."""
    qlower = query.lower()
    scores: dict[str, int] = {}
    for domain, keywords in DOMAIN_PATTERNS:
        score = sum(1 for kw in keywords if kw.lower() in qlower)
        if score > 0:
            scores[domain] = score
    return sorted(scores, key=lambda d: (-scores[d], d))


def all_domains() -> list[str]:
    """All known domain names, in canonical order."""
    return [d for d, _ in DOMAIN_PATTERNS]
