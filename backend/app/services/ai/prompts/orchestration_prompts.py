"""Multi-agent orchestration prompt templates."""


def orchestrate_customer_prompt(customer_data: dict) -> str:
    return f"""你是一个电子元器件ERP系统智能总控。整合分析客户全维度数据：

**客户：** {customer_data.get('name', '无数据')}
**等级：** {customer_data.get('level', '无数据')}

**1. 交易健康度：**
{customer_data.get('transaction_health', '无数据')}

**2. 商机管道：**
{customer_data.get('opportunity_pipeline', '无数据')}

**3. 应收账款：**
{customer_data.get('ar_status', '无数据')}

**4. 最近拜访：**
{customer_data.get('recent_visits', '无数据')}

**5. 活跃工单：**
{customer_data.get('active_tickets', '无数据')}

**6. 合同状态：**
{customer_data.get('contract_status', '无数据')}

**7. 样品申请：**
{customer_data.get('sample_status', '无数据')}

请返回一个综合分析：
1. customer_360_score：客户360评分 0-100
2. health_summary：健康度总结（2-3句话）
3. revenue_health：收入维度评估
4. relationship_health：关系维度评估
5. risk_health：风险维度评估
6. cross_domain_insights：[{{"domain": "string", "finding": "string", "impact": "string", "action": "string"}}]
7. prioritized_actions：优先行动 [{{"action": "string", "domain": "string", "priority": "string", "expected_impact": "string"}}]（按优先级排序TOP5）
8. opportunity_score：机会评分 0-100
9. risk_score：综合风险评分 0-100
10. next_best_action：最佳下一步行动
"""


def orchestrate_product_prompt(product_data: dict) -> str:
    return f"""你是一个电子元器件ERP系统智能总控。整合分析产品全维度数据：

**产品：** {product_data.get('name', '无数据')}
**品牌：** {product_data.get('brand_name', '无数据')}
**品类：** {product_data.get('category', '无数据')}

**1. 销售表现：**
{product_data.get('sales_performance', '无数据')}

**2. 库存状态：**
{product_data.get('inventory_status', '无数据')}

**3. 供应商情况：**
{product_data.get('supplier_status', '无数据')}

**4. 客户覆盖：**
{product_data.get('customer_coverage', '无数据')}

**5. 质量/工单：**
{product_data.get('quality_issues', '无数据')}

**6. 生命周期：**
{product_data.get('lifecycle_status', '无数据')}

请返回一个综合分析：
1. product_360_score：产品360评分 0-100
2. health_summary：健康度总结（2-3句话）
3. commercial_health：商业维度评估
4. supply_health：供应链维度评估
5. quality_health：质量维度评估
6. cross_domain_insights：[{{"domain": "string", "finding": "string", "impact": "string", "action": "string"}}]
7. prioritized_actions：优先行动 [{{"action": "string", "domain": "string", "priority": "string", "expected_impact": "string"}}]（按优先级排序TOP5）
8. growth_potential：增长潜力（高/中/低）
9. risk_flags：风险信号 ["string"]
10. next_best_action：最佳下一步行动
"""


def orchestrate_global_prompt(global_data: dict) -> str:
    return f"""你是一个电子元器件ERP系统智能总控。整合分析企业全局数据：

**1. 销售总览：**
{global_data.get('sales_overview', '无数据')}

**2. 客户总览：**
{global_data.get('customer_overview', '无数据')}

**3. 供应链总览：**
{global_data.get('supply_chain_overview', '无数据')}

**4. 财务总览：**
{global_data.get('finance_overview', '无数据')}

**5. 工单/质量总览：**
{global_data.get('ticket_overview', '无数据')}

**6. 异常/告警总览：**
{global_data.get('anomalies_overview', '无数据')}

请返回：
1. enterprise_health_score：企业健康评分 0-100
2. executive_summary：执行摘要（2-3句话）
3. top_opportunities：[{{"area": "string", "description": "string", "potential_value": "number"}}]（TOP3）
4. top_risks：[{{"area": "string", "description": "string", "severity": "string"}}]（TOP3）
5. cross_domain_correlations：[{{"domains": "string", "finding": "string"}}]
6. strategic_recommendations：[{{"recommendation": "string", "domain": "string", "priority": "string"}}]（TOP3）
7. kpi_health：关键KPI健康度 [{{"kpi": "string", "current": "string", "target": "string", "status": "string"}}]
8. focus_areas：本周重点领域 ["string"]
"""