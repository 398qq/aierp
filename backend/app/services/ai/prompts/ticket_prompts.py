"""Ticket intelligence prompt templates."""


def ticket_classify_prompt(ticket_data: dict) -> str:
    return f"""你是一个电子元器件技术支持专家。分类并路由客户工单：

**工单信息：**
- 标题：{ticket_data.get('title', '无')}
- 描述：{ticket_data.get('description', '无')}
- 客户：{ticket_data.get('customer_name', '无数据')}
- 当前分类：{ticket_data.get('category', '未分类')}
- 当前优先级：{ticket_data.get('priority', 'medium')}

**客户背景：**
- 客户等级：{ticket_data.get('customer_level', '无数据')}
- 历史工单数：{ticket_data.get('ticket_history', 0)}

请返回：
1. category：建议分类（技术咨询/质量问题/交付问题/商务问题/样品申请/其他）
2. subcategory：子分类 ["string"]
3. priority：建议优先级（urgent/high/medium/low）
4. priority_reason：优先级原因
5. assigned_to：建议处理人角色
6. estimated_resolution_hours：预计解决时间（小时）
7. severity：严重程度 0-100
8. escalation_needed：是否需要升级
9. auto_response_suggestion：自动回复建议
"""


def ticket_response_prompt(ticket_data: dict) -> str:
    return f"""你是一个电子元器件技术支持工程师。为工单生成回复建议：

**工单：**
- 标题：{ticket_data.get('title', '无')}
- 描述：{ticket_data.get('description', '无')}
- 分类：{ticket_data.get('category', '未分类')}

**相关产品信息：**
{ticket_data.get('product_info', '无数据')}

**历史类似工单解决方案：**
{ticket_data.get('similar_solutions', '无相似工单')}

**知识库匹配：**
{ticket_data.get('kb_matches', '无匹配')}

请返回：
1. diagnosis：问题诊断（1-2句话）
2. root_cause：可能根因
3. solution_steps：解决步骤 ["string"]
4. reply_template：回复模板
5. followup_questions：需要确认的问题 ["string"]
6. internal_notes：内部备注建议
7. faq_candidate：是否适合加入FAQ
"""


def ticket_resolution_prediction_prompt(ticket_data: dict) -> str:
    return f"""你是一个IT服务管理专家。预测工单解决时间和风险：

**工单：** {ticket_data.get('title', '无')}
**分类：** {ticket_data.get('category', '未分类')}
**优先级：** {ticket_data.get('priority', 'medium')}
**当前状态：** {ticket_data.get('status', 'open')}
**已用时间：** {ticket_data.get('elapsed_hours', 0)}小时

**历史统计：**
- 同类工单平均解决时间：{ticket_data.get('avg_resolution_hours', '无数据')}小时
- 同类工单一次性解决率：{ticket_data.get('first_contact_resolution_rate', '无数据')}%

请返回：
1. predicted_resolution_hours：预计解决总时间
2. confidence：预测置信度 0-100
3. resolution_barriers：解决障碍 ["string"]
4. stall_risk：停滞风险（低/中/高）
5. escalation_probability：升级概率%
6. customer_satisfaction_prediction：预计客户满意度（高/中/低）
7. acceleration_suggestions：加速建议 ["string"]
"""


def ticket_cluster_prompt(ticket_data: dict) -> str:
    return f"""你是一个服务质量分析专家。分析工单集群找根因：

**工单汇总：**
- 总工单数（近30天）：{ticket_data.get('total_tickets', 0)}
- 按分类分布：{ticket_data.get('category_distribution', '无数据')}
- 按优先级分布：{ticket_data.get('priority_distribution', '无数据')}
- 平均解决时间：{ticket_data.get('avg_resolution_hours', '无数据')}小时
- 满意度平均分：{ticket_data.get('avg_satisfaction', '无数据')}

**热点客户：**
{ticket_data.get('hotspot_customers', '无数据')}

**热点产品：**
{ticket_data.get('hotspot_products', '无数据')}

请返回：
1. clusters：[{{"cluster_name": "string", "ticket_count": "integer", "root_cause": "string", "severity": "string", "trend": "string"}}]
2. systemic_issues：系统性问题 ["string"]
3. product_quality_alerts：产品质量预警 ["string"]
4. process_gaps：流程缺陷 ["string"]
5. improvement_plan：改进计划 ["string"]（3条）
6. prevention_suggestions：预防建议 ["string"]
"""