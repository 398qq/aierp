"""Brand product performance prompt templates."""


def brand_product_performance_prompt(brand_data: dict) -> str:
    return f"""你是一个电子元器件产品管理专家。分析品牌下产品绩效：

**品牌：** {brand_data.get("name")} ({brand_data.get("name_cn", "")})

**产品销售数据：**
{brand_data.get("product_ranking", "无数据")}

**整体统计：**
- 产品总数：{brand_data.get("total_products", 0)}
- 有销售产品数：{brand_data.get("active_products", 0)}
- 近6月总销售额：{brand_data.get("total_revenue_6m", 0)}
- 近6月总毛利：{brand_data.get("total_margin_6m", 0)}

请返回：
1. star_products：明星产品列表 [{{"product_name": "string", "revenue": "number", "margin_pct": "number", "growth": "string", "recommendation": "string"}}]（取TOP3）
2. problem_products：问题产品列表 [{{"product_name": "string", "issue": "string", "suggestion": "string"}}]（取2个）
3. portfolio_assessment：产品组合评价（1-2句话）
4. focus_recommendations：聚焦建议 ["string"]（2-3条）
5. phase_out_candidates：淘汰候选 ["string"]（如有）
"""


def brand_customer_penetration_prompt(brand_data: dict) -> str:
    return f"""你是一个电子元器件市场分析专家。分析品牌客户渗透情况：

**品牌：** {brand_data.get("name")} ({brand_data.get("name_cn", "")})

**客户数据：**
- 已购买客户数：{brand_data.get("customer_count", 0)}
- 客户行业分布：{brand_data.get("industry_distribution", "无数据")}
- 客户等级分布：{brand_data.get("level_distribution", "无数据")}
- 重复购买率：{brand_data.get("repeat_rate", "无数据")}%
- 平均客单价：{brand_data.get("avg_order_value", "无数据")}

**未覆盖但有潜力的客户群：**
{brand_data.get("untapped_opportunities", "无数据")}

请返回：
1. penetration_score：客户渗透评分 0-100
2. penetration_assessment：渗透分析（1-2句话）
3. key_industries：核心覆盖行业 [{{"industry": "string", "customer_count": "integer", "contribution_pct": "number", "assessment": "string"}}]
4. untapped_industries：待开发行业 [{{"industry": "string", "potential_customers": "integer", "strategy": "string"}}]
5. retention_strategy：客户留存策略 ["string"]（2条）
6. expansion_strategy：扩展策略 ["string"]（2条）
"""


def brand_lifecycle_prompt(brand_data: dict) -> str:
    return f"""你是一个电子元器件产品生命周期管理专家。判断品牌所处生命周期阶段：

**品牌：** {brand_data.get("name")} ({brand_data.get("name_cn", "")})

**关键指标：**
- 产品总数：{brand_data.get("product_count", 0)}
- 近6月新品数：{brand_data.get("new_products_6m", 0)}
- EOL/NRND 产品占比：{brand_data.get("eol_pct", 0)}%
- 近12月销售增长：{brand_data.get("revenue_growth_12m", "无数据")}%
- 近12月客户增长：{brand_data.get("customer_growth_12m", "无数据")}%
- 供应商扩张/缩减：{brand_data.get("supplier_trend", "无数据")}
- 产品上市节奏：{brand_data.get("product_intro_rhythm", "无数据")}

请返回：
1. lifecycle_stage：生命周期阶段（导入期/成长期/成熟期/衰退期）
2. stage_confidence：阶段判断置信度 0-100
3. stage_evidence：阶段判断依据（2-3条）
4. strategic_advice：战略建议（投资/维持/收割/退出）+ 具体说明
5. next_12m_outlook：未来12个月展望
6. key_actions：关键行动建议 ["string"]（3条）
7. risk_signals：风险信号 ["string"]（如有）
"""


def brand_price_trends_prompt(brand_data: dict) -> str:
    return f"""你是一个电子元器件定价策略专家。分析品牌价格走势：

**品牌：** {brand_data.get("name")} ({brand_data.get("name_cn", "")})

**价格数据：**
- 近12月月度均价趋势：{brand_data.get("monthly_avg_price", "无数据")}
- 近12月月度毛利率：{brand_data.get("monthly_margin", "无数据")}
- 当前均价：{brand_data.get("current_avg_price", "无数据")}
- 12月前均价：{brand_data.get("price_12m_ago", "无数据")}
- 价格变化率：{brand_data.get("price_change_pct", "无数据")}%
- 市场基准价：{brand_data.get("market_benchmark", "无数据")}

**供应商成本：**
- 平均成本变化：{brand_data.get("cost_trend", "无数据")}

请返回：
1. price_trend：价格趋势（上涨/稳定/下降）
2. trend_score：价格健康评分 0-100
3. margin_assessment：毛利率评估（1-2句话）
4. competitiveness：价格竞争力评估（vs 市场基准）
5. pricing_issues：定价问题 ["string"]（如有）
6. optimization_suggestions：优化建议 ["string"]（2-3条）
7. opportunity_alert：价格机会/风险提示（如有）
"""
