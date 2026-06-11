"""Sales target intelligence prompt templates."""


def target_recommendation_prompt(target_data: dict) -> str:
    return f"""你是一个销售管理专家。为销售人员推荐业绩目标：

**销售人员：** {target_data.get("user_name", "无数据")}

**历史业绩：**
- 上期目标：{target_data.get("last_target", 0)}
- 上期实际：{target_data.get("last_actual", 0)}
- 达成率：{target_data.get("last_attainment", "无数据")}%
- 近12月月均：{target_data.get("monthly_avg", 0)}
- 同比增长：{target_data.get("yoy_growth", "无数据")}%

**管道数据：**
- 当前商机金额：{target_data.get("pipeline_value", 0)}
- 商机转化率：{target_data.get("conversion_rate", "无数据")}%
- 预计成交金额：{target_data.get("expected_close", 0)}

**市场和客户：**
- 负责客户数：{target_data.get("customer_count", 0)}
- 活跃客户数：{target_data.get("active_customers", 0)}
- 市场增长率：{target_data.get("market_growth", "无数据")}%

请返回：
1. recommended_target：建议目标金额
2. conservative_target：保守目标
3. ambitious_target：挑战目标
4. confidence：达成信心评分 0-100
5. growth_rate：建议增长率%
6. key_drivers：增长驱动因素 ["string"]
7. risk_factors：达不成的风险 ["string"]
8. strategy：达成策略 ["string"]（3条）
"""


def attainment_prediction_prompt(target_data: dict) -> str:
    return f"""你是一个销售预测专家。预测目标达成情况：

**当前目标：** {target_data.get("target_amount", 0)}
**当前实际：** {target_data.get("actual_amount", 0)}
**达成率：** {target_data.get("attainment_pct", "无数据")}%
**剩余天数：** {target_data.get("remaining_days", 0)}天

**趋势数据：**
- 近3月月均：{target_data.get("recent_monthly_avg", 0)}
- 本月至今：{target_data.get("mtd_amount", 0)}
- 环比增长：{target_data.get("mom_growth", "无数据")}%

**管道支持：**
- 待转化商机：{target_data.get("pipeline_opportunities", "无数据")}
- 预计转化金额：{target_data.get("expected_conversion", 0)}

请返回：
1. predicted_attainment：预计达成率%
2. predicted_amount：预计完成金额
3. gap：预计缺口金额
4. confidence：预测置信度 0-100
5. trend：趋势（超额/达成/接近/差距大）
6. key_opportunities：关键支撑商机 ["string"]
7. catch_up_plan：追赶计划 ["string"]（如有缺口）
8. early_warning：是否需要预警
"""


def target_early_warning_prompt(target_data: dict) -> str:
    return f"""你是一个销售管理预警专家。检测目标风险并发出预警：

**所有活跃目标汇总：**
{target_data.get("targets_summary", "无数据")}

**整体进度：**
- 公司总目标：{target_data.get("company_target", 0)}
- 公司总实际：{target_data.get("company_actual", 0)}
- 整体达成率：{target_data.get("overall_attainment", "无数据")}%
- 时间进度：{target_data.get("time_progress", "无数据")}%

请返回：
1. overall_status：整体状态（健康/关注/预警）
2. risk_targets：[{{"user_name": "string", "target": "number", "actual": "number", "attainment_pct": "number", "risk_level": "string", "reason": "string"}}]
3. top_performers：[{{"user_name": "string", "attainment_pct": "number", "highlight": "string"}}]
4. systemic_issues：系统性问题 ["string"]
5. recommendations：管理建议 ["string"]（3条）
6. forecast_attainment：预计最终达成率%
"""
