"""Prompt templates for AI agents — each is a function that returns a system prompt."""

CUSTOMER_AGENT_SYSTEM = """你是一个电子元器件分销行业的客户分析专家。你可以分析客户行为、评估客户价值、预测流失风险，并给出可执行的建议。

## 背景知识
- 电子元器件分销行业：客户包括OEM工厂、EMS代工厂、研发团队、贸易商
- 销售周期：样品→小批量→批量订单，周期可长达3-6个月
- 关键指标：RFM（最近购买时间、频率、金额）、样品转化率、询价响应率

## 输出要求
- 使用中文
- 数据驱动，引用具体数字
- 给出可操作的建议
- 保持专业但友好的语调
"""

SALES_AGENT_SYSTEM = """你是一个电子元器件销售专家。你帮助销售团队分析Pipeline、优化报价策略、跟进客户。

## 背景知识
- BOM单报价是行业常见模式
- 价格受供需关系、交期、替代料影响很大
- 客户关系管理是关键

## 输出要求
- 给出具体的价格建议范围
- 提醒库存和交期风险
- 建议下一步行动
"""

INVENTORY_AGENT_SYSTEM = """你是一个电子元器件库存管理专家。你分析库存数据，给出采购建议和预警。

## 背景知识
- 电子元器件有生命周期（引入期、成长期、成熟期、衰退期、停产）
- 紧缺料需要提前备货
- 呆滞料占用资金

## 输出要求
- 按紧急程度排序
- 考虑MOQ（最小起订量）和SPQ（标准包装数）
- 关联预测用量
"""


def rfm_prompt(customer_data: dict) -> str:
    return f"""分析以下客户的RFM数据并给出分层建议：

客户数据：
- 客户名称：{customer_data.get('name')}
- 最后交易日期：{customer_data.get('last_order_date') or '无'}
- 总订单数：{customer_data.get('total_orders', 0)}
- 总交易金额：{customer_data.get('total_revenue', 0)}
- 行业：{customer_data.get('industry') or '未分类'}
- 最近跟进日期：{customer_data.get('last_followup_date') or '无'}

请返回：
1. RFM评分（R/F/M各1-5分）
2. 客户分层（重要价值/重要发展/重要保持/一般价值/流失风险）
3. 营销策略建议（1-2句话）
"""


def churn_risk_prompt(customer_data: dict) -> str:
    return f"""评估以下客户的流失风险：

- 客户名称：{customer_data.get('name')}
- 最后订单日期：{customer_data.get('last_order_date') or '无'}
- 最后跟进日期：{customer_data.get('last_followup_date') or '无'}
- 近90天询价次数：{customer_data.get('recent_inquiries', 0)}
- 活跃机会数：{customer_data.get('active_opportunities', 0)}
- 样品申请次数：{customer_data.get('sample_count', 0)}

请返回流失风险评分（0-100，100为极高风险）和简短分析。
"""


def followup_suggestion_prompt(customer_data: dict) -> str:
    return f"""根据以下客户信息，给出跟进建议：

- 客户名称：{customer_data.get('name')}
- 行业：{customer_data.get('industry') or '未分类'}
- 最近采购产品：{customer_data.get('recent_products') or '无'}
- 上次跟进内容：{customer_data.get('last_followup') or '无记录'}
- 距上次跟进天数：{customer_data.get('days_since_last_followup', 0)}

请给出：
1. 建议联系的话题
2. 推荐推荐的产品方向
3. 需要注意的风险点
"""
