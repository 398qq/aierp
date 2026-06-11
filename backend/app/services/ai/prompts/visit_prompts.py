"""Visit intelligence prompt templates."""


def visit_report_prompt(visit_data: dict) -> str:
    return f"""你是一个销售拜访分析专家。根据拜访记录生成结构化报告：

**拜访信息：**
- 客户：{visit_data.get("customer_name", "无数据")}
- 日期：{visit_data.get("visit_date", "无数据")}
- 类型：{visit_data.get("type", "无数据")}
- 目的：{visit_data.get("purpose", "无数据")}
- 主要产品：{visit_data.get("main_product", "无数据")}

**拜访内容：**
{visit_data.get("content", "无内容")}

**拜访结果：**
{visit_data.get("result", "无结果")}

**关键要点：**
{visit_data.get("key_points", "无")}

**下一步计划：**
{visit_data.get("next_plan", "无")}

请返回：
1. visit_summary：拜访摘要（2-3句话）
2. key_achievements：关键成果 ["string"]
3. customer_sentiment：客户情绪（积极/中性/消极）
4. engagement_level：客户参与度（高/中/低）
5. product_interest：产品兴趣评估
6. opportunity_signals：商机信号 ["string"]
7. risk_signals：风险信号 ["string"]
8. action_items：行动项 [{{"action": "string", "priority": "string", "deadline": "string"}}]
9. followup_recommendation：跟进建议
10. effectiveness_score：拜访效果评分 0-100
"""


def visit_sentiment_prompt(visit_data: dict) -> str:
    return f"""你是一个客户交互分析师。分析拜访中的客户情感和态度：

**客户：** {visit_data.get("customer_name", "无数据")}

**拜访记录：**
- 内容：{visit_data.get("content", "无")}
- 结果：{visit_data.get("result", "无")}
- 要点：{visit_data.get("key_points", "无")}

**历史拜访摘要：**
{visit_data.get("visit_history", "无历史")}

**客户背景：**
- 合作年限：{visit_data.get("relationship_years", "无数据")}
- 近期采购变化：{visit_data.get("purchase_trend", "无数据")}

请返回：
1. overall_sentiment：整体情感（满意/中性/不满）
2. sentiment_score：情感评分 0-100
3. key_concerns：客户关注点 ["string"]
4. satisfaction_indicators：满意度指标 ["string"]
5. dissatisfaction_signals：不满信号 ["string"]
6. relationship_trend：关系趋势（改善/稳定/恶化）
7. loyalty_risk：流失风险（低/中/高）
8. improvement_suggestions：改善建议 ["string"]
"""


def visit_effectiveness_prompt(visit_data: dict) -> str:
    return f"""你是一个销售效率分析专家。评估拜访团队的整体效果：

**拜访统计：**
- 总拜访次数（近30天）：{visit_data.get("total_visits", 0)}
- 人均拜访次数：{visit_data.get("visits_per_person", 0)}
- 有商机的拜访占比：{visit_data.get("opp_conversion_rate", "无数据")}%
- 平均拜访间隔：{visit_data.get("avg_visit_interval", "无数据")}天

**客户覆盖：**
- 已拜访客户数：{visit_data.get("visited_customers", 0)}
- 高价值客户拜访覆盖率：{visit_data.get("high_value_coverage", "无数据")}%
- 未拜访客户数（超过30天）：{visit_data.get("unvisited_count", 0)}

**产出数据：**
- 拜访后新建商机：{visit_data.get("new_opps_after_visit", 0)}
- 拜访后成交金额：{visit_data.get("revenue_after_visit", 0)}
- 平均拜访成本：{visit_data.get("avg_visit_cost", "无数据")}

请返回：
1. effectiveness_score：效率评分 0-100
2. coverage_assessment：覆盖评估（1-2句话）
3. productivity_assessment：产出评估（1-2句话）
4. high_performers：高效人员特征 ["string"]
5. gaps：覆盖缺口 ["string"]
6. optimization_suggestions：优化建议 ["string"]（3条）
7. visit_frequency_recommendation：拜访频率建议
"""
