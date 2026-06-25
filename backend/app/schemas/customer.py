from datetime import datetime

from pydantic import BaseModel, Field


class CustomerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    code: str | None = None
    short_name: str | None = None
    contact_person: str | None = None
    phone: str | None = None
    email: str | None = None
    address: str | None = None
    industry: str | None = None
    level: str | None = None
    source: str | None = None
    notes: str | None = None
    customer_type: str | None = None
    region: str | None = None
    credit_limit: float | None = None
    credit_level: str | None = None
    # 2026-06-23 schema 扩展：业务必填字段（必须走 API，不再走 SQL 例外）
    unified_social_credit_code: str | None = Field(None, max_length=32, description="统一社会信用代码 18 位")
    tax_id: str | None = Field(None, max_length=32, description="纳税人识别号")
    payment_terms: str | None = Field(None, max_length=64, description="付款条件，如 月结30天/款到发货")
    payment_method: str | None = Field(None, max_length=64, description="付款方式，如 银行转账/支票/现金")
    bank_name: str | None = Field(None, max_length=128, description="开户行")
    bank_account: str | None = Field(None, max_length=64, description="银行账号")
    invoice_title: str | None = Field(None, max_length=255, description="发票抬头")
    invoice_address: str | None = Field(None, max_length=255, description="开票地址")
    invoice_phone: str | None = Field(None, max_length=32, description="开票电话")
    tax_rate: float | None = Field(None, description="税率 %")
    owner: str | None = Field(None, max_length=64, description="负责人/销售")
    default_incoterm: str | None = Field(None, max_length=32, description="默认贸易条款 EXW/FOB/CIF 等")
    currency: str | None = Field(None, max_length=8, description="默认币种 CNY/USD")
    website: str | None = Field(None, max_length=255, description="官网")
    parent_id: int | None = Field(None, description="上级客户 ID（集团关系）")
    annual_revenue: float | None = Field(None, description="年营收（元）")
    employee_count: int | None = Field(None, description="员工数")
    price_tier: str | None = Field(None, max_length=16, description="价格档位 vip_a/vip_b/normal")
    delivery_address: str | None = Field(None, description="收货地址")


class CustomerUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    code: str | None = None
    short_name: str | None = None
    contact_person: str | None = None
    phone: str | None = None
    email: str | None = None
    address: str | None = None
    industry: str | None = None
    level: str | None = None
    source: str | None = None
    notes: str | None = None
    customer_type: str | None = None
    region: str | None = None
    credit_limit: float | None = None
    credit_level: str | None = None
    # 2026-06-23 schema 扩展：业务必填字段（必须走 API，不再走 SQL 例外）
    unified_social_credit_code: str | None = Field(None, max_length=32)
    tax_id: str | None = Field(None, max_length=32)
    payment_terms: str | None = Field(None, max_length=64)
    payment_method: str | None = Field(None, max_length=64)
    bank_name: str | None = Field(None, max_length=128)
    bank_account: str | None = Field(None, max_length=64)
    invoice_title: str | None = Field(None, max_length=255)
    invoice_address: str | None = Field(None, max_length=255)
    invoice_phone: str | None = Field(None, max_length=32)
    tax_rate: float | None = None
    owner: str | None = Field(None, max_length=64)
    default_incoterm: str | None = Field(None, max_length=32)
    currency: str | None = Field(None, max_length=8)
    website: str | None = Field(None, max_length=255)
    parent_id: int | None = None
    annual_revenue: float | None = None
    employee_count: int | None = None
    price_tier: str | None = Field(None, max_length=16)
    delivery_address: str | None = None


class CustomerResponse(BaseModel):
    id: int
    code: str | None
    name: str
    short_name: str | None
    contact_person: str | None
    phone: str | None
    email: str | None
    address: str | None
    industry: str | None
    level: str | None
    source: str | None
    notes: str | None
    customer_type: str | None
    region: str | None
    credit_limit: float | None
    credit_level: str | None
    # 2026-06-23 schema 扩展
    unified_social_credit_code: str | None = None
    tax_id: str | None = None
    payment_terms: str | None = None
    payment_method: str | None = None
    bank_name: str | None = None
    bank_account: str | None = None
    invoice_title: str | None = None
    invoice_address: str | None = None
    invoice_phone: str | None = None
    tax_rate: float | None = None
    owner: str | None = None
    default_incoterm: str | None = None
    currency: str | None = None
    website: str | None = None
    parent_id: int | None = None
    annual_revenue: float | None = None
    employee_count: int | None = None
    price_tier: str | None = None
    delivery_address: str | None = None
    last_contacted_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ContactCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    title: str | None = None
    role: str | None = None
    phone: str | None = None
    email: str | None = None
    wechat: str | None = None
    is_primary: bool = False
    notes: str | None = None


class FollowUpCreate(BaseModel):
    method: str | None = None
    status: str | None = None
    content: str | None = None
    result: str | None = None
    planned_at: str | None = None
    completed_at: str | None = None
    priority: str | None = None
    assigned_to: str | None = None


class AlertRuleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    rule_type: str = Field(
        min_length=1, max_length=50
    )  # no_order, credit_over, order_drop, ar_overdue
    threshold_days: int | None = None
    threshold_pct: float | None = None
    threshold_amount: float | None = None
    enabled: bool = True
    severity: str = "warning"


class AlertRuleUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    rule_type: str | None = None
    threshold_days: int | None = None
    threshold_pct: float | None = None
    threshold_amount: float | None = None
    enabled: bool | None = None
    severity: str | None = None


class LevelRuleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    target_level: str = Field(min_length=1, max_length=20)  # A, B, C, D
    condition_type: str = Field(
        min_length=1, max_length=50
    )  # revenue, order_count, days
    operator: str = Field(min_length=1, max_length=10)  # >, <, >=, <=
    threshold_value: float
    period_days: int | None = None
    enabled: bool = True
    priority: int = 0


class LevelRuleUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    target_level: str | None = None
    condition_type: str | None = None
    operator: str | None = None
    threshold_value: float | None = None
    period_days: int | None = None
    enabled: bool | None = None
    priority: int | None = None
