"""Purchase order intelligence prompt templates."""


def po_optimization_prompt(po_data: dict) -> str:
    return f"""你是一个电子元器件采购优化专家。优化采购订单：

**采购单：** {po_data.get('order_no', '无')}
**供应商：** {po_data.get('supplier_name', '无数据')}
**总金额：** {po_data.get('total_amount', 0)}

**采购明细：**
{po_data.get('items_detail', '无数据')}

**库存状态：**
- 相关产品当前库存：{po_data.get('current_stock', '无数据')}
- 安全库存：{po_data.get('safety_stock', '无数据')}
- 近30天日均消耗：{po_data.get('daily_consumption', '无数据')}

**其他供应商报价：**
{po_data.get('alternative_quotes', '无替代报价')}

请返回：
1. optimization_score：优化评分 0-100
2. quantity_advice：[{{"product_name": "string", "ordered": "integer", "suggested": "integer", "reason": "string"}}]
3. supplier_split：分单建议 [{{"supplier_name": "string", "product_name": "string", "quantity": "integer", "price": "number", "saving": "number"}}]
4. timing_advice：采购时机建议
5. risk_flags：风险提示 ["string"]
6. total_saving_estimate：预计节省金额
"""


def po_auto_suggest_prompt(po_data: dict) -> str:
    return f"""你是一个电子元器件库存管理专家。根据库存状态建议采购：

**库存告警：**
{po_data.get('stock_alerts', '无数据')}

**低库存产品：**
{po_data.get('low_stock_items', '无数据')}

**历史采购参考：**
- 近90天采购频率：{po_data.get('purchase_frequency', '无数据')}
- 供应商报价：{po_data.get('supplier_quotes', '无数据')}
- 最小起订量：{po_data.get('moq_info', '无数据')}

请返回：
1. urgency_level：紧急程度（低/中/高/紧急）
2. suggested_pos：[{{"supplier_name": "string", "product_name": "string", "quantity": "integer", "estimated_price": "number", "estimated_amount": "number", "urgency": "string", "reason": "string"}}]
3. total_estimated_amount：预计总金额
4. prioritization：优先级排序依据
5. inventory_health_score：库存健康评分 0-100
"""


def po_risk_assessment_prompt(po_data: dict) -> str:
    return f"""你是一个电子元器件采购风控专家。评估采购订单风险：

**采购单：** {po_data.get('order_no', '无')}
**供应商：** {po_data.get('supplier_name', '无数据')}
**金额：** {po_data.get('total_amount', 0)}
**预计交期：** {po_data.get('expected_date', '无数据')}

**供应商风险：**
- 历史延迟率：{po_data.get('supplier_delay_rate', '无数据')}%
- 质量问题率：{po_data.get('supplier_quality_rate', '无数据')}%
- 财务稳定性：{po_data.get('supplier_financial', '未知')}

**单品风险：**
{po_data.get('item_risks', '无数据')}

**市场风险：**
- 品类供需状态：{po_data.get('market_supply', '未知')}
- 价格趋势：{po_data.get('price_trend', '未知')}

请返回：
1. overall_risk：整体风险等级（低/中/高）
2. risk_score：风险评分 0-100
3. risk_factors：[{{"factor": "string", "severity": "string", "impact": "string"}}]
4. delivery_risk：交付风险评估
5. price_risk：价格风险评估
6. quality_risk：质量风险评估
7. mitigation_plan：风险缓解计划 ["string"]（3条）
8. go_no_go：建议（执行/暂缓/取消）
"""