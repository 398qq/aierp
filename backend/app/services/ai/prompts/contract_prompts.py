"""Contract intelligence prompt templates."""


def contract_extract_prompt(contract_data: dict) -> str:
    return f"""你是一个商业合同分析专家。提取合同关键条款：

**合同：** {contract_data.get("title", "无")}
**合同号：** {contract_data.get("contract_no", "无")}
**客户：** {contract_data.get("customer_name", "无数据")}
**金额：** {contract_data.get("amount", 0)}
**签署日：** {contract_data.get("signed_date", "无数据")}
**到期日：** {contract_data.get("expire_date", "无数据")}

**合同备注/内容摘要：**
{contract_data.get("notes", "无")}

**关联销售订单：**
{contract_data.get("linked_orders", "无关联订单")}

请返回：
1. contract_type：合同类型判断
2. key_terms：[{{"clause": "string", "content": "string", "importance": "string", "risk_flag": "string"}}]
3. payment_terms：付款条款摘要
4. delivery_terms：交付条款摘要
5. warranty_terms：质保条款摘要
6. liability_clauses：责任条款要点
7. termination_clauses：终止条款要点
8. special_conditions：特殊条款
9. missing_clauses：缺失的重要条款 ["string"]
10. overall_risk：合同风险（低/中/高）
"""


def contract_risk_prompt(contract_data: dict) -> str:
    return f"""你是一个商业合同风险审核专家。评估合同风险：

**合同：** {contract_data.get("title", "无")}
**客户：** {contract_data.get("customer_name", "无数据")}
**金额：** {contract_data.get("amount", 0)}

**合同条款摘要：**
{contract_data.get("key_terms", "无数据")}

**客户信用：**
- 信用评级：{contract_data.get("credit_rating", "无数据")}
- 历史履约率：{contract_data.get("fulfillment_rate", "无数据")}%

请返回：
1. risk_score：风险评分 0-100
2. risk_level：风险等级（低/中/高）
3. financial_risk：财务风险评估
4. legal_risk：法律风险评估
5. operational_risk：履约风险评估
6. risk_items：[{{"item": "string", "risk": "string", "impact": "string", "mitigation": "string"}}]
7. recommendation：签署建议（建议签署/修改后签署/不建议签署）
8. negotiation_priority：谈判优先级建议 ["string"]
"""


def contract_expiry_prompt(contract_data: dict) -> str:
    return f"""你是一个合同管理专家。分析即将到期的合同并给出建议：

**即将到期合同列表：**
{contract_data.get("expiring_contracts", "无数据")}

**客户续约历史：**
{contract_data.get("renewal_history", "无数据")}

请返回：
1. expiring_soon：[{{"contract_no": "string", "customer_name": "string", "amount": "number", "expire_date": "string", "days_left": "integer", "renewal_probability": "integer", "action": "string"}}]
2. high_risk_expiries：高风险到期合同 ["string"]
3. renewal_opportunities：续约机会 ["string"]
4. total_at_risk_amount：风险总金额
5. priority_actions：优先行动 ["string"]（3条）
6. auto_renewal_candidates：建议自动续约的合同 ["string"]
"""


def contract_rebate_prompt(contract_data: dict) -> str:
    return f"""你是一个销售激励分析专家。分析合同返利和激励：

**合同：** {contract_data.get("title", "无")}
**客户：** {contract_data.get("customer_name", "无数据")}
**合同金额：** {contract_data.get("amount", 0)}

**历史采购：**
- 年度累计采购：{contract_data.get("annual_purchase", 0)}
- 季度累计采购：{contract_data.get("quarterly_purchase", 0)}
- 采购趋势：{contract_data.get("purchase_trend", "无数据")}

**返利条款：**
{contract_data.get("rebate_terms", "无数据")}

请返回：
1. rebate_achieved：已达成返利金额
2. rebate_projected：预计全年返利
3. rebate_tier_progress：返利层级进度
4. gap_to_next_tier：到达下一层还需采购额
5. optimization_suggestions：优化建议 ["string"]
6. upsell_opportunities：追加销售机会 ["string"]
7. margin_impact：返利对毛利率的影响评估
"""
