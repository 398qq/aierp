"""Finance intelligence prompt templates."""


def payment_prediction_prompt(finance_data: dict) -> str:
    return f"""你是一个企业财务风险分析师。预测回款延迟风险：

**客户回款历史：**
- 客户名称：{finance_data.get("customer_name", "无数据")}
- 历史平均回款天数：{finance_data.get("avg_payment_days", "无数据")}天
- 近12月延迟次数：{finance_data.get("late_count_12m", 0)}
- 当前应收总额：{finance_data.get("total_ar", 0)}
- 已逾期金额：{finance_data.get("overdue_amount", 0)}

**当前未结发票：**
{finance_data.get("open_invoices", "无数据")}

**客户健康度：**
- 客户等级：{finance_data.get("customer_level", "无数据")}
- 最近采购频率：{finance_data.get("recent_order_freq", "无数据")}
- 信用评级：{finance_data.get("credit_rating", "无数据")}

请返回：
1. overall_risk：整体回款风险（低/中/高）
2. risk_score：风险评分 0-100
3. late_invoice_predictions：[{{"invoice_no": "string", "amount": "number", "due_date": "string", "predicted_delay_days": "integer", "probability": "integer", "reason": "string"}}]
4. dso_forecast：预计DSO天数
5. cash_flow_impact：现金流影响评估
6. recommendations：建议措施 ["string"]（2-3条）
"""


def cash_flow_forecast_prompt(finance_data: dict) -> str:
    return f"""你是一个企业财务规划专家。预测现金流：

**当前状态：**
- 现金余额：{finance_data.get("cash_balance", 0)}
- 应收账款：{finance_data.get("total_ar", 0)}
- 应付账款：{finance_data.get("total_ap", 0)}
- 本月已回款：{finance_data.get("collected_mtd", 0)}
- 本月已付款：{finance_data.get("paid_mtd", 0)}

**未来应收：**
{finance_data.get("expected_receivables", "无数据")}

**未来应付：**
{finance_data.get("expected_payables", "无数据")}

请返回：
1. cash_flow_health：现金流健康度（差/一般/良好/优秀）
2. health_score：健康评分 0-100
3. forecast_7d：7天预测金额
4. forecast_30d：30天预测金额
5. forecast_90d：90天预测金额
6. shortage_risk：资金短缺风险（低/中/高）
7. shortage_timing：预计短缺时间点
8. recommendations：优化建议 ["string"]（3条）
9. alerts：预警 ["string"]
"""


def dunning_strategy_prompt(finance_data: dict) -> str:
    return f"""你是一个企业应收账款管理专家。制定催款策略：

**客户：** {finance_data.get("customer_name", "无数据")}
**发票号：** {finance_data.get("invoice_no", "无数据")}
**金额：** {finance_data.get("amount", 0)}
**到期日：** {finance_data.get("due_date", "无数据")}
**已逾期天数：** {finance_data.get("overdue_days", 0)}

**客户特征：**
- 客户等级：{finance_data.get("customer_level", "无数据")}
- 历史催款响应：{finance_data.get("dunning_history", "无数据")}
- 当前在途订单：{finance_data.get("pending_orders", "无数据")}
- 关系年数：{finance_data.get("relationship_years", "无数据")}年

请返回：
1. dunning_level：催款级别（温和/标准/加强/法律）
2. suggested_contact：建议联系方式
3. suggested_timing：最佳联系时间
4. message_template：催款话术模板
5. escalation_timeline：升级时间线
6. negotiation_strategy：谈判策略
7. risk_of_default：坏账风险评估
"""


def credit_risk_prompt(finance_data: dict) -> str:
    return f"""你是一个企业信用风险评估专家。评估客户信用风险：

**客户：** {finance_data.get("customer_name", "无数据")}

**交易历史：**
- 合作年限：{finance_data.get("relationship_years", 0)}年
- 累计交易额：{finance_data.get("total_revenue", 0)}
- 平均回款天数：{finance_data.get("avg_payment_days", "无数据")}天
- 逾期次数（12月）：{finance_data.get("late_count_12m", 0)}
- 最大逾期金额：{finance_data.get("max_overdue", 0)}

**当前状态：**
- 当前应收：{finance_data.get("current_ar", 0)}
- 当前逾期：{finance_data.get("current_overdue", 0)}
- 信用额度：{finance_data.get("credit_limit", "无数据")}
- 已用额度：{finance_data.get("credit_used", 0)}

请返回：
1. credit_rating：信用评级（AAA/AA/A/B/C/D）
2. credit_score：信用评分 0-100
3. recommended_credit_limit：建议信用额度
4. payment_terms_recommendation：建议付款条件
5. risk_factors：风险因素 ["string"]
6. positive_signals：积极信号 ["string"]
7. watch_list：是否建议列入关注名单
8. action_recommendation：行动建议
"""
