"""NLP query and sales enrichment prompt templates."""


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


def opportunity_enrich_prompt(ctx: dict) -> str:
    return f"""评估以下B2B电子元器件商机的风险等级、赢单概率和下一步最佳行动。

商机信息：
- 标题：{ctx['title']}
- 阶段：{ctx['stage']}
- 金额：{ctx['amount']}
- 状态：{ctx['status']}
- 备注：{ctx['notes']}

请基于电子元器件行业的销售周期特征进行评估。"""


def quotation_enrich_prompt(ctx: dict) -> str:
    items_text = "\n".join(
        f"  - {it['product_name']}: {it['quantity']}pcs x ¥{it['unit_price']} = ¥{it['total_price']}"
        for it in ctx.get('items', [])
    )
    return f"""评估以下报价单的定价健康度、赢单概率和利润空间。

报价信息：
- 总金额：¥{ctx['total_amount']}
- 状态：{ctx['status']}
- 品项数：{ctx['item_count']}

报价明细：
{items_text}

请从电子元器件行业角度评估定价合理性。"""


def sales_order_enrich_prompt(ctx: dict) -> str:
    return f"""评估以下销售订单的交货风险和回款风险。

订单信息：
- 总金额：¥{ctx['total_amount']}
- 状态：{ctx['status']}
- 下单日期：{ctx['order_date']}
- 预计交货：{ctx['delivery_date']}
- 品项数：{ctx['item_count']}
- 备注：{ctx['notes']}

请基于电子元器件行业特征评估风险。"""


def delivery_note_enrich_prompt(ctx: dict) -> str:
    return f"""评估以下发货单的完成风险和签收延迟概率。

发货信息：
- 状态：{ctx['status']}
- 发货日期：{ctx['delivery_date']}
- 签收日期：{ctx['received_date']}
- 品项数：{ctx['item_count']}
- 备注：{ctx['notes']}

请基于电子元器件行业物流特征评估风险。"""


def list_risk_summary_prompt(opps: list[dict]) -> str:
    items_text = "\n".join(
        f"  [ID:{o['id']}] {o['title']} | 阶段:{o['stage']} | 金额:{o['amount']} | 状态:{o['status']} | 赢单率:{o['win_probability']}%"
        for o in opps
    )
    return f"""批量评估以下商机列表的风险等级，为每个商机标注风险等级(low/medium/high)和需要关注的标记。

商机列表：
{items_text}

请为每个商机返回风险等级，如有异常请标注flag说明。"""


def quotation_list_enrich_prompt(quotes: list[dict]) -> str:
    items_text = "\n".join(
        f"  [ID:{q['id']}] 金额:{q['total_amount']} | 状态:{q['status']} | 品项数:{q['item_count']}"
        for q in quotes
    )
    return f"""批量评估以下报价单列表，为每个报价单标注定价健康度(good/fair/poor)和需要关注的标记。

报价单列表：
{items_text}

请为每个报价单返回健康度评估，如有异常请标注flag说明。"""


def order_list_enrich_prompt(orders: list[dict]) -> str:
    items_text = "\n".join(
        f"  [ID:{o['id']}] 金额:{o['total_amount']} | 状态:{o['status']} | 品项数:{o['item_count']}"
        for o in orders
    )
    return f"""批量评估以下销售订单列表，为每个订单标注交付风险(low/medium/high)和需要关注的标记。

订单列表：
{items_text}

请为每个订单返回风险评估，如有异常请标注flag说明。"""


def delivery_list_enrich_prompt(notes: list[dict]) -> str:
    items_text = "\n".join(
        f"  [ID:{n['id']}] 状态:{n['status']} | 品项数:{n['item_count']}"
        for n in notes
    )
    return f"""批量评估以下发货单列表，为每个发货单标注完成风险(low/medium/high)和需要关注的标记。

发货单列表：
{items_text}

请为每个发货单返回风险评估，如有异常请标注flag说明。"""


def flow_validate_quote_to_order_prompt(ctx: dict) -> str:
    return f"""验证报价单转销售订单的合理性。

报价单：总金额 ¥{ctx['total_amount']}，品项数 {ctx['item_count']}，状态 {ctx['status']}
品项：
{ctx.get('items_summary', '')}

请从价格合理性、库存可行性、客户信用等角度评估转化风险，给出建议（仅供参考，不阻断流程）。"""


def flow_validate_order_to_delivery_prompt(ctx: dict) -> str:
    return f"""验证销售订单转发货单的合理性。

订单：总金额 ¥{ctx['total_amount']}，品项数 {ctx['item_count']}，状态 {ctx['status']}
预计交货：{ctx.get('delivery_date', '')}

请从库存、物流、客户接收意愿等角度评估发货风险，给出建议（仅供参考，不阻断流程）。"""