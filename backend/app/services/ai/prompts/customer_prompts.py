"""Customer intelligence prompt templates."""

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


def rfm_prompt(customer_data: dict) -> str:
    return f"""分析以下客户的RFM数据并给出分层建议：

客户数据：
- 客户名称：{customer_data.get("name")}
- 最后交易日期：{customer_data.get("last_order_date") or "无"}
- 总订单数：{customer_data.get("total_orders", 0)}
- 总交易金额：{customer_data.get("total_revenue", 0)}
- 行业：{customer_data.get("industry") or "未分类"}
- 最近跟进日期：{customer_data.get("last_followup_date") or "无"}

请返回：
1. RFM评分（R/F/M各1-5分）
2. 客户分层（重要价值/重要发展/重要保持/一般价值/流失风险）
3. 营销策略建议（1-2句话）
"""


def churn_risk_prompt(customer_data: dict) -> str:
    return f"""评估以下客户的流失风险：

**客户档案：**
- 名称：{customer_data.get("name")}
- 行业：{customer_data.get("industry", "未知")}
- 等级：{customer_data.get("level", "未知")}
- 生命周期：{customer_data.get("lifecycle", "未知")}

**订单行为：**
- 历史总订单数：{customer_data.get("total_orders", 0)}
- 总交易金额：{customer_data.get("total_revenue", 0)}
- 最近订单日期：{customer_data.get("last_order_date") or "无"}
- 近90天订单数：{customer_data.get("orders_last_90d", 0)}
- 近180天订单数：{customer_data.get("orders_last_180d", 0)}
- 订单频次趋势：{customer_data.get("order_trend", "无数据")}

**互动指标：**
- 最近跟进日期：{customer_data.get("last_followup_date") or "无"}
- 最后联系时间：{customer_data.get("last_contacted_at") or "无"}
- 近90天询价次数：{customer_data.get("recent_inquiries", 0)}
- 活跃商机数：{customer_data.get("active_opportunities", 0)}
- 当前报价数：{customer_data.get("active_quotations", 0)}

**财务指标：**
- 信用额度利用率：{customer_data.get("credit_utilization", "无数据")}
- AR逾期天数：{customer_data.get("ar_overdue_days", 0)}

**健康评分：** {customer_data.get("health_score", "无")}/{customer_data.get("health_label", "无")}

请综合以上多维度数据，返回流失风险评分（0-100，100为极高风险）、风险等级（低/中/高）、关键风险因素列表、具体挽救建议。
"""


def followup_suggestion_prompt(customer_data: dict) -> str:
    return f"""根据以下客户信息，给出跟进建议：

- 客户名称：{customer_data.get("name")}
- 行业：{customer_data.get("industry") or "未分类"}
- 最近采购产品：{customer_data.get("recent_products") or "无"}
- 上次跟进内容：{customer_data.get("last_followup") or "无记录"}
- 距上次跟进天数：{customer_data.get("days_since_last_followup", 0)}

请给出：
1. 建议联系的话题
2. 推荐的产品方向
3. 需要注意的风险点
"""


def followup_analysis_prompt(followups_text: str, customer_name: str = "") -> str:
    return f"""分析以下客户跟进记录，提取洞察：

客户：{customer_name or "未知"}
跟进记录：
{followups_text}

请返回：
1. 整体情感倾向（积极/中性/消极）和判断理由
2. 提取关键的讨论话题（最多5个）
3. 识别行动项和待办事项
4. 标记风险信号（如：价格敏感、竞争对手介入、决策人变更、需求萎缩）
5. 生成互动摘要（2-3句话概况客户现状）
"""


def followup_recognition_prompt(text: str, customer_data: dict, now_text: str) -> str:
    return f"""请把销售输入的自然语言跟进内容识别成 ERP 跟进表单字段。

当前时间：{now_text}

客户信息：
- 客户名称：{customer_data.get("name") or "未知"}
- 行业：{customer_data.get("industry") or "未分类"}
- 等级：{customer_data.get("level") or "未知"}
- 负责人：{customer_data.get("owner") or "无"}
- 最近跟进：{customer_data.get("last_followup") or "无记录"}

销售输入：
{text}

字段规范：
- method 只能是 phone/visit/video/email/wechat/other
- status 只能是 planned/in_progress/completed/cancelled
- priority 只能是 high/medium/low
- planned_at 与 completed_at 使用 YYYY-MM-DD HH:mm:ss。无法确定就返回空字符串，不要编造具体时间。
- content 是跟进事项或沟通重点的精简描述。
- result 是已经发生的沟通结果；如果只是计划，则返回空字符串。
- assigned_to 是文本中明确提到的负责人；没有就优先用客户负责人；仍没有就空字符串。
- summary 用一句话说明识别结果。

请只提取销售输入中有依据的信息，并给出 confidence 0-1。
"""


def customer_recognition_prompt(text: str) -> str:
    return f"""请把销售输入的客户资料识别成 ERP 客户主数据表单字段。

销售输入：
{text}

字段规范：
- name：客户公司全称或主要组织名称，必须尽量提取。
- short_name：客户简称；如果文本没有明确简称，可以基于公司名称去掉“有限公司/股份有限公司/公司/集团”等后缀生成。
- customer_type 只能是 终端/贸易商/方案商/OEM，无法判断则空字符串。
- industry 只能是 汽车电子/消费电子/工业控制/通信设备/医疗器械/安防监控/其他，无法判断则空字符串。
- level 只能是 A/B/C/D，文本明确重点客户、战略客户、大客户可判断为 A；无法判断则空字符串。
- region 只能是 华东/华南/华北/华中/西南/西北/东北/海外，可根据省市粗略推断，无法判断则空字符串。
- source 只能是 展会/转介绍/线上推广/电话开发/公司资源，无法判断则空字符串。
- contact_person、phone、email、owner、address、notes 按文本提取。
- credit_limit 是数字，金额单位统一为元；无法判断则 null。
- credit_level 只能是 A/B/C/D，无法判断则空字符串。
- confidence 是 0-1。
- summary 用一句话说明识别结果。

只提取有依据的信息，不要编造电话、邮箱、负责人、授信额度。
"""


def customer_recognition_from_ocr_candidates_prompt(
    text: str, ocr_candidates: list[dict]
) -> str:
    candidate_blocks = []
    for index, candidate in enumerate(ocr_candidates[:6], start=1):
        key_hits = "、".join(candidate.get("key_hits") or []) or "无"
        candidate_blocks.append(
            "\n".join(
                [
                    f"候选 {index}",
                    f"- engine: {candidate.get('engine') or 'unknown'}",
                    f"- confidence: {candidate.get('confidence', 0)}",
                    f"- score: {candidate.get('score', 0)}",
                    f"- key_hits: {key_hits}",
                    f"- text:\n{candidate.get('text') or ''}",
                ]
            )
        )

    candidates_text = "\n\n".join(candidate_blocks) or "无"
    return f"""请把名片 OCR 结果识别成 ERP 客户主数据表单字段。

最佳合并文本：
{text}

OCR 多候选文本：
{candidates_text}

处理原则：
- 不要只依赖最佳合并文本；同一个字段在多个候选里出现时，优先选择更像真实名片字段的值。
- 电话、邮箱、公司名、联系人、地址是关键字段；如果最佳文本缺失，但其他候选明确出现，可以从其他候选补充。
- OCR 可能把空格、短横线、大小写、中文英文标签识别不一致；需要做合理归一化。
- 不要编造任何候选文本里没有依据的电话、邮箱、负责人、授信额度。

字段规范：
- name：客户公司全称或主要组织名称，必须尽量提取。
- short_name：客户简称；如果文本没有明确简称，可以基于公司名称去掉“有限公司/股份有限公司/公司/集团”等后缀生成。
- customer_type 只能是 终端/贸易商/方案商/OEM，无法判断则空字符串。
- industry 只能是 汽车电子/消费电子/工业控制/通信设备/医疗器械/安防监控/其他，无法判断则空字符串。
- level 只能是 A/B/C/D，文本明确重点客户、战略客户、大客户可判断为 A；无法判断则空字符串。
- region 只能是 华东/华南/华北/华中/西南/西北/东北/海外，可根据省市粗略推断，无法判断则空字符串。
- source 只能是 展会/转介绍/线上推广/电话开发/公司资源，无法判断则空字符串。
- contact_person、phone、email、owner、address、notes 按 OCR 候选提取。
- credit_limit 是数字，金额单位统一为元；无法判断则 null。
- credit_level 只能是 A/B/C/D，无法判断则空字符串。
- confidence 是 0-1。
- summary 用一句话说明识别结果，并说明是否使用了多个 OCR 候选交叉补全。

只提取有依据的信息，不要编造电话、邮箱、负责人、授信额度。
"""


def alert_enrichment_prompt(alert: dict) -> str:
    return f"""你是一个电子元器件分销行业的客户管理专家。以下是一个客户预警，请给出专业的处理建议。

预警类型：{alert.get("rule_type")}
预警名称：{alert.get("rule_name")}
严重程度：{alert.get("severity")}
预警详情：{alert.get("message")}

客户信息：
- 名称：{alert.get("customer_name")}
- 行业：{alert.get("industry", "")}
- 等级：{alert.get("level", "")}
- 最近跟进：{alert.get("last_contact", "无")}

请返回：
1. 建议的跟进方式（电话/邮件/拜访）和时机
2. 沟通要点（2-3条具体建议）
3. 邮件/消息模板（可直接使用的文本）
4. 如果处理不当最严重的后果（1句话）
"""
