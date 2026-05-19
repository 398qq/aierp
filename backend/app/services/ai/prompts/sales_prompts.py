"""Sales intelligence prompt templates."""


def quote_assist_prompt(customer_text: str, items_text: str) -> str:
    return f"""你是一个电子元器件销售策略专家。当前正在为以下客户制作报价单，请基于完整背景给出智能辅助建议：

**客户信息：**
{customer_text}

**报价行项目：**
{items_text}

请返回：
1. win_probability：预计赢单概率 0-100（综合考虑客户关系、价格竞争力、供应风险）
2. win_probability_reason：概率判断理由（1句话）
3. pricing_recommendations：每个产品的定价建议 [{{"product_name": "string", "recommended_price": "number", "price_range_low": "number", "price_range_high": "number", "margin_pct": "number", "rationale": "string"}}]
4. cross_sell_suggestions：交叉销售建议 [{{"brand_name": "string", "product_name": "string", "reason": "string", "estimated_value": "number"}}]（2条）
5. risk_summary：风险总结（1-2句话，关注库存不足、单源供应、客户信用等）
6. negotiation_tips：谈判建议 ["string"]（3条）
"""


def watchtower_prompt(alert_text: str, total_alerts: int) -> str:
    return f"""你是一个ERP系统监控专家。以下是系统自动扫描发现的异常，请给出优先级评估和行动建议：

**异常总数：{total_alerts}**

**异常详情：**
{alert_text}

请返回：
1. severity：总体严重程度（正常/需关注/紧急）
2. summary：总体评估（2-3句话）
3. top_actions：优先采取的行动 ["string"]（3条，按紧急程度排序）
4. risk_areas：识别的风险领域 ["string"]（2-3条）
"""


def customer_product_matching_prompt(customer_profile: str, candidates_text: str) -> str:
    return f"""你是一个电子元器件销售策略专家。基于客户画像推荐最合适的产品：

**客户画像：**
{customer_profile}

**候选产品（此客户尚未购买）：**
{candidates_text}

请返回：
1. recommendations：推荐产品列表 [{{"product_name": "string", "brand": "string", "reason": "string", "priority": "string: 高/中/低", "estimated_potential": "string"}}]
2. summary：推荐理由总述
3. approach_strategy：向客户推荐这些产品的策略建议
"""


def product_customer_matching_prompt(product_profile: str, candidates_text: str) -> str:
    return f"""你是一个电子元器件销售策略专家。为一个新产品推荐最可能采购的客户：

**产品画像：**
{product_profile}

**候选客户：**
{candidates_text}

请返回：
1. recommendations：推荐客户列表 [{{"customer_name": "string", "reason": "string", "priority": "string: 高/中/低", "estimated_potential": "string"}}]
2. summary：推荐理由总述
3. outreach_strategy：与这些客户建立联系的最佳策略
"""