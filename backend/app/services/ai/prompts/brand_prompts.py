"""Brand intelligence prompt templates."""


def brand_profile_prompt(brand_data: dict) -> str:
    return f"""为以下电子元器件品牌生成完整画像：

**基础信息：**
- 品牌名：{brand_data.get("name")}
- 中文名：{brand_data.get("name_cn", "")}
- 分类：{brand_data.get("category", "未知")}
- 官网：{brand_data.get("website", "未知")}
- 备注：{brand_data.get("notes", "")}

**产品数据：**
- 产品总数：{brand_data.get("product_count", 0)}
- 产品分类分布：{brand_data.get("category_distribution", "")}
- 封装类型分布：{brand_data.get("package_distribution", "")}
- 代表产品：{brand_data.get("sample_products", "")}
- 供应商覆盖：{brand_data.get("supplier_count", 0)} 家

请生成：
1. market_position：市场地位（国际一线/国际二线/国产替代/国产新兴/专业细分）
2. brand_strength_score：品牌实力评分 0-100
3. technology_advantages：技术优势领域（3条）
4. target_markets：主要目标市场（3-5个）
5. competitive_advantages：竞争优势（3条）
6. typical_applications：典型应用方向（3个）
7. key_competitors：主要竞争对手品牌（2-3个）
8. procurement_difficulty：采购难度（容易/中等/困难）及原因
9. price_positioning：价格定位（高端/中端/经济型）
10. recommendation：对该品牌的合作建议（1-2句话）
"""


def brand_import_prompt(raw_text: str) -> str:
    return f"""从以下文本中提取电子元器件品牌信息：

原始文本：
{raw_text}

请提取：
1. name：品牌英文名
2. name_cn：品牌中文名（如有）
3. category：主要产品分类（如：电源管理/MCU/被动器件/连接器等）
4. website：官网URL（如有）
5. description：品牌简介（1-2句话）
6. product_lines：主要产品线描述
"""


def brand_portfolio_prompt(brand_data: dict) -> str:
    return f"""分析以下电子元器件品牌的产品组合：

**品牌：** {brand_data.get("name")} ({brand_data.get("name_cn", "")})

**产品数据：**
- 产品总数：{brand_data.get("product_count", 0)}
- 分类分布：{brand_data.get("category_distribution", "")}
- 封装分布：{brand_data.get("package_distribution", "")}
- 价格区间：{brand_data.get("price_range", "无数据")}
- 供应商数：{brand_data.get("supplier_count", 0)}
- 代表产品：{brand_data.get("sample_products", "")}

请分析：
1. portfolio_strength：产品线完整度（完整/较全/聚焦/单一）
2. category_analysis：各类别详细分析 [{{"category", "count", "pct", "assessment"}}]
3. growth_areas：增长方向建议（2条）
4. gap_analysis：产品线缺口（2条）
5. cross_sell_opportunities：交叉销售机会（2条）
6. inventory_health：库存健康度评估
"""


def brand_compare_prompt(brand_a: dict, brand_b: dict, overlap: dict) -> str:
    return f"""对比两个电子元器件品牌：

**品牌A：** {brand_a.get("name")} ({brand_a.get("name_cn", "")})
- 分类：{brand_a.get("category")}
- 产品数：{brand_a.get("product_count", 0)}
- 代表产品：{brand_a.get("sample_products", "")}

**品牌B：** {brand_b.get("name")} ({brand_b.get("name_cn", "")})
- 分类：{brand_b.get("category")}
- 产品数：{brand_b.get("product_count", 0)}
- 代表产品：{brand_b.get("sample_products", "")}

**重叠分析：**
- 共同分类：{overlap.get("shared_categories", "")}
- 竞争产品数：{overlap.get("overlapping_products", 0)}

请返回：
1. comparison_summary：对比总结（1-2句话）
2. dimension_scores：维度评分 {{a, b}} 各维度0-10分 [{{"dimension", "a_score", "b_score", "note"}}]
3. switching_feasibility：替换可行性（容易/中等/困难）
4. switching_notes：替换注意事项（3条）
5. recommended_strategy：推荐策略（以A为主/以B为主/双源/视产品而定）
"""


def brand_health_prompt(brand_data: dict) -> str:
    return f"""你是一个电子元器件供应链分析专家。分析以下品牌经营健康度：

**品牌：** {brand_data.get("name")} ({brand_data.get("name_cn", "")})
**分类：** {brand_data.get("category", "未知")}

**销售数据（最近12个月）：**
- 月度收入趋势：{brand_data.get("monthly_revenue", "无数据")}
- 月度毛利率趋势：{brand_data.get("monthly_margin", "无数据")}
- 总订单数：{brand_data.get("total_orders", 0)}
- 活跃客户数：{brand_data.get("active_customers", 0)}
- 退货率：{brand_data.get("return_rate", "无数据")}%
- 收入增长率（环比）：{brand_data.get("revenue_growth", "无数据")}%
- 客户流失率：{brand_data.get("churn_rate", "无数据")}%

**库存数据：**
- 当前总库存：{brand_data.get("total_stock", 0)}
- 库存周转率：{brand_data.get("turnover_rate", "无数据")}
- 滞销品占比：{brand_data.get("slow_moving_pct", "无数据")}%

请返回：
1. overall_health_score：综合健康评分 0-100
2. health_label：健康等级（优秀/良好/一般/需关注/风险）
3. revenue_assessment：收入评估（1-2句话）
4. margin_assessment：利润评估（1-2句话）
5. customer_assessment：客户健康度评估（1-2句话）
6. inventory_assessment：库存健康度评估（1-2句话）
7. trend_direction：趋势方向（上升/稳定/下降）
8. risk_signals：风险信号 ["string"]（2-3条）
9. improvement_suggestions：改进建议 ["string"]（2-3条）
"""


def brand_risk_prompt(brand_data: dict) -> str:
    return f"""你是一个电子元器件供应链风险管理专家。评估以下品牌的风险：

**品牌：** {brand_data.get("name")} ({brand_data.get("name_cn", "")})

**供应商风险：**
- 供应商总数：{brand_data.get("supplier_count", 0)}
- 单源产品数：{brand_data.get("single_source_count", 0)}/{brand_data.get("product_count", 0)}
- 单源产品占比：{brand_data.get("single_source_pct", 0)}%
- 主要供应商集中度：{brand_data.get("top_supplier_share", "无数据")}%

**产品生命周期风险：**
- 产品总数：{brand_data.get("product_count", 0)}
- EOL/NRND 产品数：{brand_data.get("eol_count", 0)}
- 近6月新品数：{brand_data.get("new_products_6m", 0)}

**客户集中度风险：**
- 活跃客户数：{brand_data.get("active_customers", 0)}
- Top1客户收入占比：{brand_data.get("top_customer_share", 0)}%
- Top3客户收入占比：{brand_data.get("top3_customer_share", 0)}%

**市场风险：**
- 竞争对手品牌数：{brand_data.get("competitor_count", 0)}
- 可替代产品占比：{brand_data.get("substitutable_pct", 0)}%

请返回：
1. risk_score：综合风险评分 0-100（越高风险越大）
2. risk_level：风险等级（低/中/高/严重）
3. supplier_risk：供应商风险评估 + 评分 0-100
4. lifecycle_risk：产品生命周期风险评估 + 评分 0-100
5. concentration_risk：客户集中度风险评估 + 评分 0-100
6. market_risk：市场可替代风险评估 + 评分 0-100
7. top_risks：主要风险项 ["string"]（3条，按严重程度排序）
8. mitigation_suggestions：缓解建议 ["string"]（3条）
"""


def brand_supplier_matrix_prompt(brand_data: dict) -> str:
    return f"""你是一个电子元器件采购策略专家。分析以下品牌的供应商矩阵：

**品牌：** {brand_data.get("name")} ({brand_data.get("name_cn", "")})

**供应商覆盖情况：**
- 产品总数：{brand_data.get("product_count", 0)}
- 供应商总数：{brand_data.get("supplier_count", 0)}
- 供应商覆盖明细：{brand_data.get("supplier_details", "无数据")}
- 平均每供应商产品数：{brand_data.get("avg_products_per_supplier", 0)}
- 产品替代覆盖率：{brand_data.get("backup_coverage_pct", 0)}%

**价格分析：**
- 价格区间：{brand_data.get("price_range", "无数据")}
- 各供应商价格竞争力：{brand_data.get("supplier_price_ranking", "无数据")}

**交期分析：**
- 平均交期：{brand_data.get("avg_lead_time", "无数据")}天
- 最短/最长交期：{brand_data.get("lead_time_range", "无数据")}

请返回：
1. overall_assessment：供应商矩阵总体评估（1-2句话）
2. coverage_score：供应商覆盖评分 0-100
3. single_source_products：单源风险产品清单 [{{"product_name": "string", "supplier": "string", "cost_price": "number", "risk_reason": "string"}}]
4. backup_recommendations：备选供应商建议 [{{"current": "string", "recommended": "string", "reason": "string"}}]
5. price_optimization：价格优化建议 ["string"]
6. negotiation_leverage：议价空间分析
"""


def brand_recommendation_prompt(brand_data: dict) -> str:
    return f"""你是一个电子元器件销售策略专家。基于品牌购买关联数据给出推荐：

**源品牌：** {brand_data.get("name")} ({brand_data.get("name_cn", "")})
**分类：** {brand_data.get("category", "未知")}
**产品数：** {brand_data.get("product_count", 0)}
**活跃客户数：** {brand_data.get("active_customers", 0)}

**关联购买数据（购买了此品牌的客户还购买了）：**
{brand_data.get("co_purchase_data", "无数据")}

**潜在可推荐品牌（含客户重叠度）：**
{brand_data.get("candidate_brands", "无数据")}

请返回：
1. recommendation_summary：推荐总结（1-2句话）
2. recommended_brands：推荐品牌列表 [{{"brand_name": "string", "overlap_score": "number 0-100", "reason": "string", "priority": "string: 高/中/低"}}]
3. cross_sell_strategies：交叉销售策略 ["string"]（2-3条）
4. target_industries：适合推荐的客户行业 ["string"]
5. expected_conversion：预期转化率评估（1句话）
"""
