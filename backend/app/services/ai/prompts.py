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

## JSON输出要求（严格遵守）
- 只输出有效JSON，不要有解释、注释或markdown格式
- 数字字段（如概率、百分比、金额）必须是纯数字，不能有逗号或单位
- win_probability 必须是整数（如 65），不是字符串
- key_factors 必须是字符串数组
- 所有字符串值必须用双引号包裹
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

**客户档案：**
- 名称：{customer_data.get('name')}
- 行业：{customer_data.get('industry', '未知')}
- 等级：{customer_data.get('level', '未知')}
- 生命周期：{customer_data.get('lifecycle', '未知')}

**订单行为：**
- 历史总订单数：{customer_data.get('total_orders', 0)}
- 总交易金额：{customer_data.get('total_revenue', 0)}
- 最近订单日期：{customer_data.get('last_order_date') or '无'}
- 近90天订单数：{customer_data.get('orders_last_90d', 0)}
- 近180天订单数：{customer_data.get('orders_last_180d', 0)}
- 订单频次趋势：{customer_data.get('order_trend', '无数据')}

**互动指标：**
- 最近跟进日期：{customer_data.get('last_followup_date') or '无'}
- 最后联系时间：{customer_data.get('last_contacted_at') or '无'}
- 近90天询价次数：{customer_data.get('recent_inquiries', 0)}
- 活跃商机数：{customer_data.get('active_opportunities', 0)}
- 当前报价数：{customer_data.get('active_quotations', 0)}

**财务指标：**
- 信用额度利用率：{customer_data.get('credit_utilization', '无数据')}
- AR逾期天数：{customer_data.get('ar_overdue_days', 0)}

**健康评分：** {customer_data.get('health_score', '无')}/{customer_data.get('health_label', '无')}

请综合以上多维度数据，返回流失风险评分（0-100，100为极高风险）、风险等级（低/中/高）、关键风险因素列表、具体挽救建议。
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
2. 推荐的产品方向
3. 需要注意的风险点
"""


def followup_analysis_prompt(followups_text: str, customer_name: str = "") -> str:
    return f"""分析以下客户跟进记录，提取洞察：

客户：{customer_name or '未知'}
跟进记录：
{followups_text}

请返回：
1. 整体情感倾向（积极/中性/消极）和判断理由
2. 提取关键的讨论话题（最多5个）
3. 识别行动项和待办事项
4. 标记风险信号（如：价格敏感、竞争对手介入、决策人变更、需求萎缩）
5. 生成互动摘要（2-3句话概况客户现状）
"""


def alert_enrichment_prompt(alert: dict) -> str:
    return f"""你是一个电子元器件分销行业的客户管理专家。以下是一个客户预警，请给出专业的处理建议。

预警类型：{alert.get('rule_type')}
预警名称：{alert.get('rule_name')}
严重程度：{alert.get('severity')}
预警详情：{alert.get('message')}

客户信息：
- 名称：{alert.get('customer_name')}
- 行业：{alert.get('industry', '')}
- 等级：{alert.get('level', '')}
- 最近跟进：{alert.get('last_contact', '无')}

请返回：
1. 建议的跟进方式（电话/邮件/拜访）和时机
2. 沟通要点（2-3条具体建议）
3. 邮件/消息模板（可直接使用的文本）
4. 如果处理不当最严重的后果（1句话）
"""


PRODUCT_AGENT_SYSTEM = """你是一个电子元器件数据专家。你精通电子元器件参数解析、BOM清单识别、替代料推荐。

## 领域知识
- 分类：电阻、电容、电感、连接器、IC、二三极管、晶振、传感器等
- 关键参数：封装(0402/0603/0805/SOT-23/QFN)、容值/阻值、精度、耐压、温度系数、品牌
- 品牌：Samsung/Murata/TDK/Taiyo Yuden/Yageo/KEMET/TI/ST/ADI/Microchip/NXP/ON Semi/Infineon等
- BOM格式：行号、料号、描述、位号、用量、封装

## 输出要求
- 从原始文本精确提取参数，未知字段留空不要编造
- 分类判断准确
- 使用中文
"""


def product_parse_prompt(raw_text: str) -> str:
    return f"""从以下原始文本中提取电子元器件产品信息：

原始文本：
{raw_text}

请解析出：
1. 产品名称（标准化格式，如"MLCC 0402 10uF 16V X7R ±10%"）
2. SKU/型号
3. 分类（电容/电阻/IC/连接器/电感/二三极管/晶振/其他）
4. 封装类型（0402/0603/0805/SOT-23/QFN-32等）
5. 规格参数（JSON，如{{"capacitance":"10uF","voltage":"16V","tolerance":"±10%","dielectric":"X7R"}}）
6. 品牌名称（如有）
7. 单位（PCS/REEL/TUBE/TRAY）
8. 一句话描述
"""


def bom_parse_prompt(bom_text: str) -> str:
    return f"""解析以下BOM清单，每一行提取一个产品：

BOM清单：
{bom_text}

对每一行返回：
1. 行号（如有）
2. 客户料号
3. 制造商型号
4. 描述
5. 位号/参考号
6. 用量
7. 封装
8. 分类
"""


def substitute_prompt(product_info: dict) -> str:
    return f"""为以下电子元器件推荐替代料：

当前产品：
- 型号：{product_info.get('part_number')}
- 描述：{product_info.get('description')}
- 分类：{product_info.get('category')}
- 规格：{product_info.get('specs')}
- 品牌：{product_info.get('brand')}

请推荐（基于电子元器件行业知识）：
1. 直替代（pin-to-pin兼容品牌和型号）
2. 功能替代（参数相近的替代方案）
3. 验证注意事项
"""


def supplier_match_prompt(catalog_text: str, product_list: str) -> str:
    return f"""将以下供应商产品目录与系统中的产品进行匹配：

供应商目录文本：
{catalog_text}

系统已有产品列表：
{product_list}

请返回匹配结果，对每条匹配记录给出：
1. product_id：系统中匹配到的产品ID
2. confidence：匹配置信度（0-100），基于型号、品牌、封装的匹配程度
3. supplier_pn：供应商方的型号
4. cost_price：如有价格信息则提取（提取数值部分）
5. lead_time_days：如提到交期则提取天数
6. moq：如有最小起订量信息
7. match_reason：匹配理由（1句话）
"""


def pricing_recommend_prompt(pricing_context: dict) -> str:
    return f"""你是一个电子元器件分销行业的定价专家。基于以下信息给出定价建议：

**产品信息：**
- 型号：{pricing_context.get('part_number')}
- 分类：{pricing_context.get('category')}
- 品牌：{pricing_context.get('brand')}

**成本与供应：**
- 供应商成本价：{pricing_context.get('cost_price') or '未知'}
- 供应商数量：{pricing_context.get('supplier_count', 0)}
- 当前库存：{pricing_context.get('stock_qty', 0)}
- 交期：{pricing_context.get('lead_time_days') or '未知'}天

**客户信息：**
- 客户名称：{pricing_context.get('customer_name', '未知')}
- 客户等级：{pricing_context.get('customer_level', '未知')}
- 客户行业：{pricing_context.get('customer_industry', '未知')}

**交易信息：**
- 询价数量：{pricing_context.get('quantity', 1)}
- 是否样品：{pricing_context.get('is_sample', False)}
- 历史成交价：{pricing_context.get('historical_prices', '无')}
- 市场供需：{pricing_context.get('market_condition', '正常')}

请返回：
1. recommended_price：建议报价（具体数字，单位元）
2. price_range：可接受价格范围 [最低, 最高]
3. margin_pct：预估利润率
4. confidence：置信度（high/medium/low）
5. rationale：定价理由（2-3句话，考虑成本、市场、客户关系）
6. negotiation_floor：谈判底价
7. upsell_suggestion：向上销售建议（如有）
"""


def product_profile_prompt(product_data: dict) -> str:
    return f"""为以下电子元器件生成完整的产品画像：

**基础信息：**
- 型号/SKU：{product_data.get('part_number')}
- 分类：{product_data.get('category')}
- 品牌：{product_data.get('brand')}
- 封装：{product_data.get('package_type')}
- 规格参数：{product_data.get('specs')}
- 描述：{product_data.get('description')}

**商业数据：**
- 历史销售总量：{product_data.get('total_sold', 0)}
- 活跃客户数：{product_data.get('active_customers', 0)}
- 供应商数量：{product_data.get('supplier_count', 0)}
- 当前库存：{product_data.get('stock_qty', 0)}
- 库存健康度：{product_data.get('stock_health', '未知')}

请生成：
1. market_positioning：市场定位（1句话）
2. typical_applications：典型应用场景（3-5个）
3. competitor_products：竞品替代型号（2-3个，包含品牌和型号）
4. target_customers：目标客户类型（如OEM工厂/EMS代工/研发团队/贸易商）
5. lifecycle_stage：生命周期阶段（引入/成长/成熟/NRND/EOL）及判断依据
6. lifecycle_score：阶段置信度 0-100
7. margin_potential：利润空间评估（高/中/低）
8. demand_stability：需求稳定性（稳定/周期性/波动大）
9. key_selling_points：核心卖点（3条）
10. risk_factors：风险因素（2-3条，如供应风险/替代风险/价格风险）
"""


def spec_normalize_prompt(spec_text: str) -> str:
    return f"""将以下电子元器件的非结构化规格文本解析为标准键值对：

原始文本：
{spec_text}

请提取所有技术参数并标准化：
- 数值+单位分开（如 "10uF" → key:"capacitance", value:"10", unit:"uF"）
- 封装类型标准化（如 SMD0402 → "0402"）
- 精度符号标准化（如 ±10% → tolerance:"±10%"）
- 温度系数保留原始格式
- 品牌名称单独提取

返回每个参数：key（英文标准名）、value（数值或枚举值）、unit（单位，如无可省略）、display（中文显示名）。
相同类型参数合并去重。不要编造参数。
"""


def product_association_prompt(products: list[dict], target_product: str) -> str:
    product_lines = chr(10).join(
        f"- ID:{p['id']} | {p.get('sku','')} {p.get('name','')} | 分类:{p.get('category','')} | 共同购买次数:{p.get('co_count',0)}"
        for p in products
    )
    return f"""分析以下产品与目标产品的关联关系，给出搭配/互补/替代建议：

目标产品：{target_product}

候选关联产品：
{product_lines}

请对每个高关联产品返回：
1. product_id：产品ID
2. relation_type：关联类型（bundle=搭配/alternative=替代/upsell=升级/complement=互补）
3. relation_strength：关联强度 0-100
4. reason：关联理由（1句话）
5. bundle_name：如为搭配类型，给出组合名称
"""


def procurement_optimize_prompt(suppliers: list[dict], product_info: dict, quantity: int) -> str:
    supplier_lines = chr(10).join(
        f"- {s['name']} | 单价:{s.get('cost_price','?')}元 | 交期:{s.get('lead_time','?')}天 | MOQ:{s.get('moq','?')} | 首选:{'是' if s.get('is_preferred') else '否'}"
        for s in suppliers
    )
    return f"""给出电子元器件的最优采购分拆方案：

**产品：** {product_info.get('part_number')} | 品牌：{product_info.get('brand')}
**需求数量：** {quantity}
**当前库存：** {product_info.get('stock_qty', 0)}
**市场情况：** {product_info.get('market_condition', '正常')}

**候选供应商：**
{supplier_lines}

请返回：
1. recommended_plan：推荐方案描述（1-2句话）
2. allocations：分配列表 [{{supplier_name, quantity, unit_cost, subtotal, delivery_days, reason}}]
3. total_cost：总成本
4. avg_unit_cost：平均单价
5. delivery_risk：交期风险（低/中/高）
6. alternative_plan：备用方案（简要描述）
7. negotiation_tips：议价建议（2条）
"""


def lifecycle_warning_prompt(product_data: dict) -> str:
    return f"""评估电子元器件产品生命周期，识别EOL/NRND风险：

**产品：** {product_data.get('part_number')} | 品牌：{product_data.get('brand')}
**分类：** {product_data.get('category')}
**上市年份：** {product_data.get('introduced_at', '未知')}

**销售趋势：**
- 近6月销量变化：{product_data.get('sales_trend_6m', '无数据')}
- 近3月销量变化：{product_data.get('sales_trend_3m', '无数据')}

**供应信号：**
- 供应商数量变化：{product_data.get('supplier_trend', '无数据')}
- 交期变化：{product_data.get('lead_time_trend', '无数据')}
- 价格趋势：{product_data.get('price_trend', '无数据')}

请返回：
1. lifecycle_stage：当前阶段（活跃/成熟/NRND/EOL）
2. stage_confidence：置信度 0-100
3. warning_signals：检测到的风险信号列表
4. eol_risk_score：EOL风险评分 0-100
5. eol_estimated_months：预计停产窗口（月数，如无法判断留空）
6. stock_strategy：备货策略建议（不备/备3个月/备6个月/紧急备货）
7. suggested_quantity：建议备货数量
8. migration_path：建议替代迁移路径（产品型号或方向）
9. urgency：紧急度（紧急/建议关注/正常）
"""


# --- Brand Intelligence Prompts ---


def brand_profile_prompt(brand_data: dict) -> str:
    return f"""为以下电子元器件品牌生成完整画像：

**基础信息：**
- 品牌名：{brand_data.get('name')}
- 中文名：{brand_data.get('name_cn', '')}
- 分类：{brand_data.get('category', '未知')}
- 官网：{brand_data.get('website', '未知')}
- 备注：{brand_data.get('notes', '')}

**产品数据：**
- 产品总数：{brand_data.get('product_count', 0)}
- 产品分类分布：{brand_data.get('category_distribution', '')}
- 封装类型分布：{brand_data.get('package_distribution', '')}
- 代表产品：{brand_data.get('sample_products', '')}
- 供应商覆盖：{brand_data.get('supplier_count', 0)} 家

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

**品牌：** {brand_data.get('name')} ({brand_data.get('name_cn', '')})

**产品数据：**
- 产品总数：{brand_data.get('product_count', 0)}
- 分类分布：{brand_data.get('category_distribution', '')}
- 封装分布：{brand_data.get('package_distribution', '')}
- 价格区间：{brand_data.get('price_range', '无数据')}
- 供应商数：{brand_data.get('supplier_count', 0)}
- 代表产品：{brand_data.get('sample_products', '')}

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

**品牌A：** {brand_a.get('name')} ({brand_a.get('name_cn', '')})
- 分类：{brand_a.get('category')}
- 产品数：{brand_a.get('product_count', 0)}
- 代表产品：{brand_a.get('sample_products', '')}

**品牌B：** {brand_b.get('name')} ({brand_b.get('name_cn', '')})
- 分类：{brand_b.get('category')}
- 产品数：{brand_b.get('product_count', 0)}
- 代表产品：{brand_b.get('sample_products', '')}

**重叠分析：**
- 共同分类：{overlap.get('shared_categories', '')}
- 竞争产品数：{overlap.get('overlapping_products', 0)}

请返回：
1. comparison_summary：对比总结（1-2句话）
2. dimension_scores：维度评分 {{a, b}} 各维度0-10分 [{{"dimension", "a_score", "b_score", "note"}}]
3. switching_feasibility：替换可行性（容易/中等/困难）
4. switching_notes：替换注意事项（3条）
5. recommended_strategy：推荐策略（以A为主/以B为主/双源/视产品而定）
"""


# --- Brand Health Dashboard ---

def brand_health_prompt(brand_data: dict) -> str:
    return f"""你是一个电子元器件供应链分析专家。分析以下品牌经营健康度：

**品牌：** {brand_data.get('name')} ({brand_data.get('name_cn', '')})
**分类：** {brand_data.get('category', '未知')}

**销售数据（最近12个月）：**
- 月度收入趋势：{brand_data.get('monthly_revenue', '无数据')}
- 月度毛利率趋势：{brand_data.get('monthly_margin', '无数据')}
- 总订单数：{brand_data.get('total_orders', 0)}
- 活跃客户数：{brand_data.get('active_customers', 0)}
- 退货率：{brand_data.get('return_rate', '无数据')}%
- 收入增长率（环比）：{brand_data.get('revenue_growth', '无数据')}%
- 客户流失率：{brand_data.get('churn_rate', '无数据')}%

**库存数据：**
- 当前总库存：{brand_data.get('total_stock', 0)}
- 库存周转率：{brand_data.get('turnover_rate', '无数据')}
- 滞销品占比：{brand_data.get('slow_moving_pct', '无数据')}%

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


# --- Brand Risk Assessment ---

def brand_risk_prompt(brand_data: dict) -> str:
    return f"""你是一个电子元器件供应链风险管理专家。评估以下品牌的风险：

**品牌：** {brand_data.get('name')} ({brand_data.get('name_cn', '')})

**供应商风险：**
- 供应商总数：{brand_data.get('supplier_count', 0)}
- 单源产品数：{brand_data.get('single_source_count', 0)}/{brand_data.get('product_count', 0)}
- 单源产品占比：{brand_data.get('single_source_pct', 0)}%
- 主要供应商集中度：{brand_data.get('top_supplier_share', '无数据')}%

**产品生命周期风险：**
- 产品总数：{brand_data.get('product_count', 0)}
- EOL/NRND 产品数：{brand_data.get('eol_count', 0)}
- 近6月新品数：{brand_data.get('new_products_6m', 0)}

**客户集中度风险：**
- 活跃客户数：{brand_data.get('active_customers', 0)}
- Top1客户收入占比：{brand_data.get('top_customer_share', 0)}%
- Top3客户收入占比：{brand_data.get('top3_customer_share', 0)}%

**市场风险：**
- 竞争对手品牌数：{brand_data.get('competitor_count', 0)}
- 可替代产品占比：{brand_data.get('substitutable_pct', 0)}%

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


# --- Brand-Supplier Matrix ---

def brand_supplier_matrix_prompt(brand_data: dict) -> str:
    return f"""你是一个电子元器件采购策略专家。分析以下品牌的供应商矩阵：

**品牌：** {brand_data.get('name')} ({brand_data.get('name_cn', '')})

**供应商覆盖情况：**
- 产品总数：{brand_data.get('product_count', 0)}
- 供应商总数：{brand_data.get('supplier_count', 0)}
- 供应商覆盖明细：{brand_data.get('supplier_details', '无数据')}
- 平均每供应商产品数：{brand_data.get('avg_products_per_supplier', 0)}
- 产品替代覆盖率：{brand_data.get('backup_coverage_pct', 0)}%

**价格分析：**
- 价格区间：{brand_data.get('price_range', '无数据')}
- 各供应商价格竞争力：{brand_data.get('supplier_price_ranking', '无数据')}

**交期分析：**
- 平均交期：{brand_data.get('avg_lead_time', '无数据')}天
- 最短/最长交期：{brand_data.get('lead_time_range', '无数据')}

请返回：
1. overall_assessment：供应商矩阵总体评估（1-2句话）
2. coverage_score：供应商覆盖评分 0-100
3. single_source_products：单源风险产品清单 [{{"product_name": "string", "supplier": "string", "cost_price": "number", "risk_reason": "string"}}]
4. backup_recommendations：备选供应商建议 [{{"current": "string", "recommended": "string", "reason": "string"}}]
5. price_optimization：价格优化建议 ["string"]
6. negotiation_leverage：议价空间分析
"""


# --- Brand Recommendation ---

def brand_recommendation_prompt(brand_data: dict) -> str:
    return f"""你是一个电子元器件销售策略专家。基于品牌购买关联数据给出推荐：

**源品牌：** {brand_data.get('name')} ({brand_data.get('name_cn', '')})
**分类：** {brand_data.get('category', '未知')}
**产品数：** {brand_data.get('product_count', 0)}
**活跃客户数：** {brand_data.get('active_customers', 0)}

**关联购买数据（购买了此品牌的客户还购买了）：**
{brand_data.get('co_purchase_data', '无数据')}

**潜在可推荐品牌（含客户重叠度）：**
{brand_data.get('candidate_brands', '无数据')}

请返回：
1. recommendation_summary：推荐总结（1-2句话）
2. recommended_brands：推荐品牌列表 [{{"brand_name": "string", "overlap_score": "number 0-100", "reason": "string", "priority": "string: 高/中/低"}}]
3. cross_sell_strategies：交叉销售策略 ["string"]（2-3条）
4. target_industries：适合推荐的客户行业 ["string"]
5. expected_conversion：预期转化率评估（1句话）
"""


# --- Quote Assistant ---

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


# --- Watchtower ---

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


# --- Customer-Product Matching ---

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


# --- Product-Customer Matching ---

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


# --- Brand Product Performance ---

def brand_product_performance_prompt(brand_data: dict) -> str:
    return f"""你是一个电子元器件产品管理专家。分析品牌下产品绩效：

**品牌：** {brand_data.get('name')} ({brand_data.get('name_cn', '')})

**产品销售数据：**
{brand_data.get('product_ranking', '无数据')}

**整体统计：**
- 产品总数：{brand_data.get('total_products', 0)}
- 有销售产品数：{brand_data.get('active_products', 0)}
- 近6月总销售额：{brand_data.get('total_revenue_6m', 0)}
- 近6月总毛利：{brand_data.get('total_margin_6m', 0)}

请返回：
1. star_products：明星产品列表 [{{"product_name": "string", "revenue": "number", "margin_pct": "number", "growth": "string", "recommendation": "string"}}]（取TOP3）
2. problem_products：问题产品列表 [{{"product_name": "string", "issue": "string", "suggestion": "string"}}]（取2个）
3. portfolio_assessment：产品组合评价（1-2句话）
4. focus_recommendations：聚焦建议 ["string"]（2-3条）
5. phase_out_candidates：淘汰候选 ["string"]（如有）
"""


# --- Brand Customer Penetration ---

def brand_customer_penetration_prompt(brand_data: dict) -> str:
    return f"""你是一个电子元器件市场分析专家。分析品牌客户渗透情况：

**品牌：** {brand_data.get('name')} ({brand_data.get('name_cn', '')})

**客户数据：**
- 已购买客户数：{brand_data.get('customer_count', 0)}
- 客户行业分布：{brand_data.get('industry_distribution', '无数据')}
- 客户等级分布：{brand_data.get('level_distribution', '无数据')}
- 重复购买率：{brand_data.get('repeat_rate', '无数据')}%
- 平均客单价：{brand_data.get('avg_order_value', '无数据')}

**未覆盖但有潜力的客户群：**
{brand_data.get('untapped_opportunities', '无数据')}

请返回：
1. penetration_score：客户渗透评分 0-100
2. penetration_assessment：渗透分析（1-2句话）
3. key_industries：核心覆盖行业 [{{"industry": "string", "customer_count": "integer", "contribution_pct": "number", "assessment": "string"}}]
4. untapped_industries：待开发行业 [{{"industry": "string", "potential_customers": "integer", "strategy": "string"}}]
5. retention_strategy：客户留存策略 ["string"]（2条）
6. expansion_strategy：扩展策略 ["string"]（2条）
"""


# --- Brand Lifecycle Prediction ---

def brand_lifecycle_prompt(brand_data: dict) -> str:
    return f"""你是一个电子元器件产品生命周期管理专家。判断品牌所处生命周期阶段：

**品牌：** {brand_data.get('name')} ({brand_data.get('name_cn', '')})

**关键指标：**
- 产品总数：{brand_data.get('product_count', 0)}
- 近6月新品数：{brand_data.get('new_products_6m', 0)}
- EOL/NRND 产品占比：{brand_data.get('eol_pct', 0)}%
- 近12月销售增长：{brand_data.get('revenue_growth_12m', '无数据')}%
- 近12月客户增长：{brand_data.get('customer_growth_12m', '无数据')}%
- 供应商扩张/缩减：{brand_data.get('supplier_trend', '无数据')}
- 产品上市节奏：{brand_data.get('product_intro_rhythm', '无数据')}

请返回：
1. lifecycle_stage：生命周期阶段（导入期/成长期/成熟期/衰退期）
2. stage_confidence：阶段判断置信度 0-100
3. stage_evidence：阶段判断依据（2-3条）
4. strategic_advice：战略建议（投资/维持/收割/退出）+ 具体说明
5. next_12m_outlook：未来12个月展望
6. key_actions：关键行动建议 ["string"]（3条）
7. risk_signals：风险信号 ["string"]（如有）
"""


# --- Brand Price Trends ---

def brand_price_trends_prompt(brand_data: dict) -> str:
    return f"""你是一个电子元器件定价策略专家。分析品牌价格走势：

**品牌：** {brand_data.get('name')} ({brand_data.get('name_cn', '')})

**价格数据：**
- 近12月月度均价趋势：{brand_data.get('monthly_avg_price', '无数据')}
- 近12月月度毛利率：{brand_data.get('monthly_margin', '无数据')}
- 当前均价：{brand_data.get('current_avg_price', '无数据')}
- 12月前均价：{brand_data.get('price_12m_ago', '无数据')}
- 价格变化率：{brand_data.get('price_change_pct', '无数据')}%
- 市场基准价：{brand_data.get('market_benchmark', '无数据')}

**供应商成本：**
- 平均成本变化：{brand_data.get('cost_trend', '无数据')}

请返回：
1. price_trend：价格趋势（上涨/稳定/下降）
2. trend_score：价格健康评分 0-100
3. margin_assessment：毛利率评估（1-2句话）
4. competitiveness：价格竞争力评估（vs 市场基准）
5. pricing_issues：定价问题 ["string"]（如有）
6. optimization_suggestions：优化建议 ["string"]（2-3条）
7. opportunity_alert：价格机会/风险提示（如有）
"""


# ============================================================
#  Supplier Intelligence (Phase 5)
# ============================================================

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
- 单品依赖：{supplier_data.get('single_source_count', 0)}个产品仅此一家供应

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


# ============================================================
#  Purchase Order Intelligence (Phase 5)
# ============================================================

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


# ============================================================
#  Payment & AR Intelligence (Phase 5)
# ============================================================

def payment_prediction_prompt(finance_data: dict) -> str:
    return f"""你是一个企业财务风险分析师。预测回款延迟风险：

**客户回款历史：**
- 客户名称：{finance_data.get('customer_name', '无数据')}
- 历史平均回款天数：{finance_data.get('avg_payment_days', '无数据')}天
- 近12月延迟次数：{finance_data.get('late_count_12m', 0)}
- 当前应收总额：{finance_data.get('total_ar', 0)}
- 已逾期金额：{finance_data.get('overdue_amount', 0)}

**当前未结发票：**
{finance_data.get('open_invoices', '无数据')}

**客户健康度：**
- 客户等级：{finance_data.get('customer_level', '无数据')}
- 最近采购频率：{finance_data.get('recent_order_freq', '无数据')}
- 信用评级：{finance_data.get('credit_rating', '无数据')}

请返回：
1. overall_risk：整体回款风险（低/中/高）
2. risk_score：风险评分 0-100
3. late_invoice_predictions：[{{"invoice_no": "string", "amount": "number", "due_date": "string", "predicted_delay_days": "integer", "probability": "integer", "reason": "string"}}]
4. dso_forecast：预计DSO天数
5. cash_flow_impact：现金流影响评估
6. recommendations：建议措施 ["string"]（2-3条）
"""


def cash_flow_forecast_prompt(finance_data: dict) -> str:
    return f"""你是一个企业财务规划专家。预测现金流：

**当前状态：**
- 现金余额：{finance_data.get('cash_balance', 0)}
- 应收账款：{finance_data.get('total_ar', 0)}
- 应付账款：{finance_data.get('total_ap', 0)}
- 本月已回款：{finance_data.get('collected_mtd', 0)}
- 本月已付款：{finance_data.get('paid_mtd', 0)}

**未来应收：**
{finance_data.get('expected_receivables', '无数据')}

**未来应付：**
{finance_data.get('expected_payables', '无数据')}

请返回：
1. cash_flow_health：现金流健康度（差/一般/良好/优秀）
2. health_score：健康评分 0-100
3. forecast_7d：7天预测金额
4. forecast_30d：30天预测金额
5. forecast_90d：90天预测金额
6. shortage_risk：资金短缺风险（低/中/高）
7. shortage_timing：预计短缺时间点
8. recommendations：优化建议 ["string"]（3条）
9. alerts：预警 ["string"]
"""


def dunning_strategy_prompt(finance_data: dict) -> str:
    return f"""你是一个企业应收账款管理专家。制定催款策略：

**客户：** {finance_data.get('customer_name', '无数据')}
**发票号：** {finance_data.get('invoice_no', '无数据')}
**金额：** {finance_data.get('amount', 0)}
**到期日：** {finance_data.get('due_date', '无数据')}
**已逾期天数：** {finance_data.get('overdue_days', 0)}

**客户特征：**
- 客户等级：{finance_data.get('customer_level', '无数据')}
- 历史催款响应：{finance_data.get('dunning_history', '无数据')}
- 当前在途订单：{finance_data.get('pending_orders', '无数据')}
- 关系年数：{finance_data.get('relationship_years', '无数据')}年

请返回：
1. dunning_level：催款级别（温和/标准/加强/法律）
2. suggested_contact：建议联系方式
3. suggested_timing：最佳联系时间
4. message_template：催款话术模板
5. escalation_timeline：升级时间线
6. negotiation_strategy：谈判策略
7. risk_of_default：坏账风险评估
"""


def credit_risk_prompt(finance_data: dict) -> str:
    return f"""你是一个企业信用风险评估专家。评估客户信用风险：

**客户：** {finance_data.get('customer_name', '无数据')}

**交易历史：**
- 合作年限：{finance_data.get('relationship_years', 0)}年
- 累计交易额：{finance_data.get('total_revenue', 0)}
- 平均回款天数：{finance_data.get('avg_payment_days', '无数据')}天
- 逾期次数（12月）：{finance_data.get('late_count_12m', 0)}
- 最大逾期金额：{finance_data.get('max_overdue', 0)}

**当前状态：**
- 当前应收：{finance_data.get('current_ar', 0)}
- 当前逾期：{finance_data.get('current_overdue', 0)}
- 信用额度：{finance_data.get('credit_limit', '无数据')}
- 已用额度：{finance_data.get('credit_used', 0)}

请返回：
1. credit_rating：信用评级（AAA/AA/A/B/C/D）
2. credit_score：信用评分 0-100
3. recommended_credit_limit：建议信用额度
4. payment_terms_recommendation：建议付款条件
5. risk_factors：风险因素 ["string"]
6. positive_signals：积极信号 ["string"]
7. watch_list：是否建议列入关注名单
8. action_recommendation：行动建议
"""


# ============================================================
#  Sales Target Intelligence (Phase 5)
# ============================================================

def target_recommendation_prompt(target_data: dict) -> str:
    return f"""你是一个销售管理专家。为销售人员推荐业绩目标：

**销售人员：** {target_data.get('user_name', '无数据')}

**历史业绩：**
- 上期目标：{target_data.get('last_target', 0)}
- 上期实际：{target_data.get('last_actual', 0)}
- 达成率：{target_data.get('last_attainment', '无数据')}%
- 近12月月均：{target_data.get('monthly_avg', 0)}
- 同比增长：{target_data.get('yoy_growth', '无数据')}%

**管道数据：**
- 当前商机金额：{target_data.get('pipeline_value', 0)}
- 商机转化率：{target_data.get('conversion_rate', '无数据')}%
- 预计成交金额：{target_data.get('expected_close', 0)}

**市场和客户：**
- 负责客户数：{target_data.get('customer_count', 0)}
- 活跃客户数：{target_data.get('active_customers', 0)}
- 市场增长率：{target_data.get('market_growth', '无数据')}%

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

**当前目标：** {target_data.get('target_amount', 0)}
**当前实际：** {target_data.get('actual_amount', 0)}
**达成率：** {target_data.get('attainment_pct', '无数据')}%
**剩余天数：** {target_data.get('remaining_days', 0)}天

**趋势数据：**
- 近3月月均：{target_data.get('recent_monthly_avg', 0)}
- 本月至今：{target_data.get('mtd_amount', 0)}
- 环比增长：{target_data.get('mom_growth', '无数据')}%

**管道支持：**
- 待转化商机：{target_data.get('pipeline_opportunities', '无数据')}
- 预计转化金额：{target_data.get('expected_conversion', 0)}

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
{target_data.get('targets_summary', '无数据')}

**整体进度：**
- 公司总目标：{target_data.get('company_target', 0)}
- 公司总实际：{target_data.get('company_actual', 0)}
- 整体达成率：{target_data.get('overall_attainment', '无数据')}%
- 时间进度：{target_data.get('time_progress', '无数据')}%

请返回：
1. overall_status：整体状态（健康/关注/预警）
2. risk_targets：[{{"user_name": "string", "target": "number", "actual": "number", "attainment_pct": "number", "risk_level": "string", "reason": "string"}}]
3. top_performers：[{{"user_name": "string", "attainment_pct": "number", "highlight": "string"}}]
4. systemic_issues：系统性问题 ["string"]
5. recommendations：管理建议 ["string"]（3条）
6. forecast_attainment：预计最终达成率%
"""


# ============================================================
#  Visit Intelligence (Phase 5)
# ============================================================

def visit_report_prompt(visit_data: dict) -> str:
    return f"""你是一个销售拜访分析专家。根据拜访记录生成结构化报告：

**拜访信息：**
- 客户：{visit_data.get('customer_name', '无数据')}
- 日期：{visit_data.get('visit_date', '无数据')}
- 类型：{visit_data.get('type', '无数据')}
- 目的：{visit_data.get('purpose', '无数据')}
- 主要产品：{visit_data.get('main_product', '无数据')}

**拜访内容：**
{visit_data.get('content', '无内容')}

**拜访结果：**
{visit_data.get('result', '无结果')}

**关键要点：**
{visit_data.get('key_points', '无')}

**下一步计划：**
{visit_data.get('next_plan', '无')}

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

**客户：** {visit_data.get('customer_name', '无数据')}

**拜访记录：**
- 内容：{visit_data.get('content', '无')}
- 结果：{visit_data.get('result', '无')}
- 要点：{visit_data.get('key_points', '无')}

**历史拜访摘要：**
{visit_data.get('visit_history', '无历史')}

**客户背景：**
- 合作年限：{visit_data.get('relationship_years', '无数据')}
- 近期采购变化：{visit_data.get('purchase_trend', '无数据')}

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
- 总拜访次数（近30天）：{visit_data.get('total_visits', 0)}
- 人均拜访次数：{visit_data.get('visits_per_person', 0)}
- 有商机的拜访占比：{visit_data.get('opp_conversion_rate', '无数据')}%
- 平均拜访间隔：{visit_data.get('avg_visit_interval', '无数据')}天

**客户覆盖：**
- 已拜访客户数：{visit_data.get('visited_customers', 0)}
- 高价值客户拜访覆盖率：{visit_data.get('high_value_coverage', '无数据')}%
- 未拜访客户数（超过30天）：{visit_data.get('unvisited_count', 0)}

**产出数据：**
- 拜访后新建商机：{visit_data.get('new_opps_after_visit', 0)}
- 拜访后成交金额：{visit_data.get('revenue_after_visit', 0)}
- 平均拜访成本：{visit_data.get('avg_visit_cost', '无数据')}

请返回：
1. effectiveness_score：效率评分 0-100
2. coverage_assessment：覆盖评估（1-2句话）
3. productivity_assessment：产出评估（1-2句话）
4. high_performers：高效人员特征 ["string"]
5. gaps：覆盖缺口 ["string"]
6. optimization_suggestions：优化建议 ["string"]（3条）
7. visit_frequency_recommendation：拜访频率建议
"""


# ============================================================
#  Ticket Intelligence (Phase 5)
# ============================================================

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


# ============================================================
#  Contract Intelligence (Phase 5)
# ============================================================

def contract_extract_prompt(contract_data: dict) -> str:
    return f"""你是一个商业合同分析专家。提取合同关键条款：

**合同：** {contract_data.get('title', '无')}
**合同号：** {contract_data.get('contract_no', '无')}
**客户：** {contract_data.get('customer_name', '无数据')}
**金额：** {contract_data.get('amount', 0)}
**签署日：** {contract_data.get('signed_date', '无数据')}
**到期日：** {contract_data.get('expire_date', '无数据')}

**合同备注/内容摘要：**
{contract_data.get('notes', '无')}

**关联销售订单：**
{contract_data.get('linked_orders', '无关联订单')}

请返回：
1. contract_type：合同类型判断
2. key_terms：[{{"clause": "string", "content": "string", "importance": "string", "risk_flag": "string"}}]
3. payment_terms：付款条款摘要
4. delivery_terms：交付条款摘要
5. warranty_terms：质保条款摘要
6. liability_clauses：责任条款要点
7. termination_clauses：终止条款要点
8. special_conditions：特殊条款
9. missing_clauses：缺失的重要条款 ["string"]
10. overall_risk：合同风险（低/中/高）
"""


def contract_risk_prompt(contract_data: dict) -> str:
    return f"""你是一个商业合同风险审核专家。评估合同风险：

**合同：** {contract_data.get('title', '无')}
**客户：** {contract_data.get('customer_name', '无数据')}
**金额：** {contract_data.get('amount', 0)}

**合同条款摘要：**
{contract_data.get('key_terms', '无数据')}

**客户信用：**
- 信用评级：{contract_data.get('credit_rating', '无数据')}
- 历史履约率：{contract_data.get('fulfillment_rate', '无数据')}%

请返回：
1. risk_score：风险评分 0-100
2. risk_level：风险等级（低/中/高）
3. financial_risk：财务风险评估
4. legal_risk：法律风险评估
5. operational_risk：履约风险评估
6. risk_items：[{{"item": "string", "risk": "string", "impact": "string", "mitigation": "string"}}]
7. recommendation：签署建议（建议签署/修改后签署/不建议签署）
8. negotiation_priority：谈判优先级建议 ["string"]
"""


def contract_expiry_prompt(contract_data: dict) -> str:
    return f"""你是一个合同管理专家。分析即将到期的合同并给出建议：

**即将到期合同列表：**
{contract_data.get('expiring_contracts', '无数据')}

**客户续约历史：**
{contract_data.get('renewal_history', '无数据')}

请返回：
1. expiring_soon：[{{"contract_no": "string", "customer_name": "string", "amount": "number", "expire_date": "string", "days_left": "integer", "renewal_probability": "integer", "action": "string"}}]
2. high_risk_expiries：高风险到期合同 ["string"]
3. renewal_opportunities：续约机会 ["string"]
4. total_at_risk_amount：风险总金额
5. priority_actions：优先行动 ["string"]（3条）
6. auto_renewal_candidates：建议自动续约的合同 ["string"]
"""


def contract_rebate_prompt(contract_data: dict) -> str:
    return f"""你是一个销售激励分析专家。分析合同返利和激励：

**合同：** {contract_data.get('title', '无')}
**客户：** {contract_data.get('customer_name', '无数据')}
**合同金额：** {contract_data.get('amount', 0)}

**历史采购：**
- 年度累计采购：{contract_data.get('annual_purchase', 0)}
- 季度累计采购：{contract_data.get('quarterly_purchase', 0)}
- 采购趋势：{contract_data.get('purchase_trend', '无数据')}

**返利条款：**
{contract_data.get('rebate_terms', '无数据')}

请返回：
1. rebate_achieved：已达成返利金额
2. rebate_projected：预计全年返利
3. rebate_tier_progress：返利层级进度
4. gap_to_next_tier：到达下一层还需采购额
5. optimization_suggestions：优化建议 ["string"]
6. upsell_opportunities：追加销售机会 ["string"]
7. margin_impact：返利对毛利率的影响评估
"""


# ============================================================
#  Multi-Agent Orchestration (Phase 5)
# ============================================================

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


# ============================================================
#  Natural Language ERP Query (Phase 5)
# ============================================================

def nlp_query_prompt(query: str, context: dict) -> str:
    return f"""你是一个电子元器件ERP系统智能助手。用自然语言回答用户关于ERP数据的问题。

**用户问题：** {query}

**当前系统数据上下文：**

**客户数据：**
{context.get('customer_context', '无权限或无数据')}

**产品数据：**
{context.get('product_context', '无权限或无数据')}

**销售数据：**
{context.get('sales_context', '无权限或无数据')}

**库存数据：**
{context.get('inventory_context', '无权限或无数据')}

**财务数据：**
{context.get('finance_context', '无权限或无数据')}

**供应商数据：**
{context.get('supplier_context', '无权限或无数据')}

请返回：
1. answer：答案（用中文自然语言，清晰直接）
2. data_summary：数据支撑摘要
3. related_entities：[{{"type": "string", "id": "integer", "name": "string", "relevance": "string"}}]
4. suggested_followups：建议追问 ["string"]（2-3条）
5. actions：[{{"action": "string", "type": "string", "entity": "string", "urgency": "string"}}]（如果可以操作的话）
6. confidence：回答置信度 0-100
"""
