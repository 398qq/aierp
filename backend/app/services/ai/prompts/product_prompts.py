"""Product intelligence prompt templates."""

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