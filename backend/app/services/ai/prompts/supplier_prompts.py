"""Supplier intelligence prompt templates."""


def supplier_scorecard_prompt(supplier_data: dict) -> str:
    return f"""你是一个电子元器件供应链管理专家。评估供应商综合绩效：

**供应商：** {supplier_data.get('name')}

**基本数据：**
- 产品线：{supplier_data.get('product_lines', '无数据')}
- 合作产品数：{supplier_data.get('product_count', 0)}
- 平均采购价：{supplier_data.get('avg_purchase_price', '无数据')}

**交付绩效：**
- 近12月采购次数：{supplier_data.get('po_count_12m', 0)}
- 按时交付率：{supplier_data.get('on_time_rate', '无数据')}%
- 平均交付周期：{supplier_data.get('avg_lead_time', '无数据')}天
- 承诺交付周期：{supplier_data.get('promised_lead_time', '无数据')}天

**质量与价格：**
- 质量问题次数：{supplier_data.get('quality_issues', 0)}
- 价格竞争力评估：{supplier_data.get('price_competitiveness', '无数据')}
- 价格波动：{supplier_data.get('price_volatility', '无数据')}

请返回：
1. overall_score：综合评分 0-100
2. delivery_score：交付评分 0-100
3. quality_score：质量评分 0-100
4. price_score：价格评分 0-100
5. stability_score：稳定性评分 0-100
6. assessment：综合评价（1-2句话）
7. strengths：优势 ["string"]（2-3条）
8. weaknesses：劣势 ["string"]（2-3条）
9. tier：供应商等级（A/B/C/D）
10. recommendations：改进建议 ["string"]（2-3条）
"""


def supplier_delay_prediction_prompt(supplier_data: dict) -> str:
    return f"""你是一个电子元器件供应链风险分析师。预测供应商交付延迟风险：

**供应商：** {supplier_data.get('name')}

**历史交付：**
- 近6月订单数：{supplier_data.get('recent_orders', 0)}
- 近6月延迟次数：{supplier_data.get('recent_delays', 0)}
- 平均延迟天数：{supplier_data.get('avg_delay_days', 0)}天
- 延迟趋势：{supplier_data.get('delay_trend', '无数据')}

**当前状态：**
- 在途订单数：{supplier_data.get('pending_orders', 0)}
- 在途金额：{supplier_data.get('pending_amount', 0)}
- 最近交付日期：{supplier_data.get('last_delivery_date', '无数据')}

**外部因素：**
- 行业交付风险：{supplier_data.get('industry_risk', '未知')}
- 地域风险：{supplier_data.get('region_risk', '未知')}

请返回：
1. delay_risk：延迟风险等级（低/中/高）
2. risk_score：风险评分 0-100
3. predicted_delay_days：预计延迟天数
4. probability：延迟概率 0-100%
5. risk_factors：风险因素 ["string"]
6. mitigation：缓解措施 ["string"]（2-3条）
7. alternative_suggestion：替代供应商建议
"""


def supplier_alternatives_prompt(supplier_data: dict) -> str:
    return f"""你是一个电子元器件供应链优化专家。为供应商推荐替代方案：

**当前供应商：** {supplier_data.get('name')}
**产品线：** {supplier_data.get('product_lines', '无数据')}

**当前供应商风险：**
- 综合评分：{supplier_data.get('score', '无数据')}
- 延迟风险：{supplier_data.get('delay_risk', '无数据')}
- 价格竞争力：{supplier_data.get('price_competitiveness', '无数据')}

**可选替代供应商：**
{supplier_data.get('candidates', '无候选供应商')}

请返回：
1. urgency：替代紧迫度（低/中/高）
2. recommended_alternatives：[{{"supplier_name": "string", "product_lines": "string", "score": "integer", "advantage": "string", "switch_cost": "string"}}]（取TOP3）
3. diversification_strategy：分散策略 ["string"]（2-3条）
4. risk_assessment：风控评估（1-2句话）
"""


def supplier_price_variance_prompt(supplier_data: dict) -> str:
    return f"""你是一个电子元器件采购成本分析师。检测供应商价格异常：

**供应商：** {supplier_data.get('name')}

**价格数据：**
- 当前平均采购价：{supplier_data.get('current_avg_price', '无数据')}
- 3月前平均价：{supplier_data.get('price_3m_ago', '无数据')}
- 6月前平均价：{supplier_data.get('price_6m_ago', '无数据')}
- 价格变化率：{supplier_data.get('price_change_pct', '无数据')}%

**市场对比：**
- 市场基准价：{supplier_data.get('market_benchmark', '无数据')}
- 同品类供应商均价：{supplier_data.get('peer_avg_price', '无数据')}
- 溢价/折价：{supplier_data.get('premium_discount', '无数据')}

**单品价格异常：**
{supplier_data.get('anomaly_products', '无数据')}

请返回：
1. price_status：价格状态（偏高/正常/偏低）
2. variance_score：异常评分 0-100
3. anomaly_products：[{{"product_name": "string", "current_price": "number", "expected_price": "number", "variance_pct": "number", "reason": "string"}}]
4. trend_analysis：趋势分析（1-2句话）
5. cost_saving_opportunities：降本机会 ["string"]（2-3条）
6. negotiation_points：议价要点 ["string"]（2-3条）
"""


def supplier_360_prompt(supplier_data: dict) -> str:
    return f"""你是一个电子元器件分销行业的供应商管理专家。请对以下供应商进行全面的360度分析评估：

**基本信息：**
- 供应商名称：{supplier_data.get('name')}
- 类型：{supplier_data.get('supplier_type', '未知')}
- 认证：{supplier_data.get('certifications', '未知')}
- 区域：{supplier_data.get('region', '未知')}
- 产品线：{supplier_data.get('product_lines', '未知')}
- 财务评级：{supplier_data.get('financial_rating', '未知')}

**采购绩效：**
{str(supplier_data.get('po_history_summary', {}))}

请返回供应商360度评估，只包含以下6个字段：
1. overall_score：综合评分 0-100 的整数
2. tier：等级，只能是 A/B/C/D 之一
3. summary：一句话综合评估（20字以内）
4. assessment：综合评估文本，涵盖交付、质量、价格、稳定性、风险（50-100字）
5. key_strengths：核心优势，字符串数组，3-5条
6. key_weaknesses：主要劣势，字符串数组，2-3条
7. recommendations：改进建议，字符串数组，3-5条
"""


def supplier_negotiation_prompt(neg_data: dict) -> str:
    return f"""你是一个电子元器件分销行业资深采购谈判专家。请基于以下供应商数据生成谈判策略：

**供应商信息：**
- 名称：{neg_data.get('name')}
- 类型：{neg_data.get('supplier_type', '未知')}
- 产品线：{neg_data.get('product_lines', '未知')}
- 财务评级：{neg_data.get('financial_rating', '未知')}
- 区域：{neg_data.get('region', '未知')}

**采购数据：**
- 历史采购总额：{neg_data.get('total_amount', 0)}元
- 采购订单数：{neg_data.get('po_count', 0)}
- 关联产品数：{neg_data.get('product_count', 0)}
- 平均采购价：{neg_data.get('avg_price', '无数据')}

**市场数据：**
- 替代供应商数：{neg_data.get('alternative_count', 0)}
- 价格竞争力：{neg_data.get('price_competitiveness', '未知')}

请给出：
1. negotiation_strategy：谈判策略（1-2句话）
2. price_target：建议目标价格描述
3. talking_points：谈判要点 ["string"]（4-6条）
4. leverage_points：我方优势筹码 ["string"]（2-3条）
5. fallback_plan：备选方案
6. suggested_approach：建议沟通方式
"""


def supplier_comparison_prompt(comparison_data: dict) -> str:
    suppliers = str(comparison_data.get('suppliers', []))
    return f"""你是一个电子元器件分销行业采购决策专家。请比较以下供应商：

**参与比较的供应商数据：**
{suppliers}

请从以下维度进行综合比较：
1. comparison_matrix：[{{"dimension": "string", "weight": "number", "scores": {{"supplier_name": score}}}}] — 各维度评分(0-100)
2. overall_ranking：[{{"rank": "integer", "supplier_name": "string", "total_score": "number", "tier": "string"}}]
3. best_in_category：[{{"category": "string", "winner": "string", "reason": "string"}}]
4. recommendation：最终推荐建议
5. summary：比较总结

比较维度包括但不限于：价格竞争力、交付准时率、质量水平、产品线覆盖、技术支持、认证资质、财务稳定性、合作关系、响应速度。
"""