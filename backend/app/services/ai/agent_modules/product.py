"""ProductAgent — AI product data extraction, BOM parsing, and substitute matching.

The product-domain AI agent. Powers the price-import and product
detail AI features.
"""
from __future__ import annotations

import logging

from app.services.ai.client import ai_client
from app.services.ai.prompts import (
    PRODUCT_AGENT_SYSTEM,
    bom_parse_prompt,
    product_parse_prompt,
    substitute_prompt,
)

logger = logging.getLogger(__name__)


class ProductAgent:
    """AI-powered product data extraction, BOM parsing, and substitute matching."""

    @staticmethod
    async def parse_product(raw_text: str) -> dict:
        """Extract structured product fields from unstructured text."""
        schema = {
            "name": "string: standardized product name",
            "sku": "string | null",
            "category": "string: 电容/电阻/IC/连接器/电感/二三极管/晶振/其他",
            "package_type": "string | null",
            "specs": "object: key-value parameter pairs",
            "brand_name": "string | null",
            "unit": "string | null",
            "description": "string: one-line summary",
        }
        try:
            return await ai_client.chat_structured(
                [
                    {"role": "system", "content": PRODUCT_AGENT_SYSTEM},
                    {"role": "user", "content": product_parse_prompt(raw_text)},
                ],
                schema,
            )
        except Exception as e:
            logger.error(f"Product parse failed: {e}")
            return {"name": "", "sku": None, "category": None, "package_type": None,
                    "specs": {}, "brand_name": None, "unit": None, "description": f"解析失败: {e}"}

    @staticmethod
    async def parse_bom(bom_text: str) -> list[dict]:
        """Parse a BOM list into an array of product entries."""
        schema = {
            "items": "list of dicts: {line_no, customer_pn, mfr_pn, description, reference, quantity, package, category}"
        }
        try:
            result = await ai_client.chat_structured(
                [
                    {"role": "system", "content": PRODUCT_AGENT_SYSTEM},
                    {"role": "user", "content": bom_parse_prompt(bom_text)},
                ],
                schema,
            )
            return result.get("items", [])
        except Exception as e:
            logger.error(f"BOM parse failed: {e}")
            return []

    @staticmethod
    async def suggest_substitutes(product_info: dict) -> dict:
        """Recommend substitute parts based on product specs."""
        schema = {
            "direct_substitutes": "list of strings: pin-to-pin compatible alternatives",
            "functional_substitutes": "list of strings: functionally equivalent alternatives",
            "verification_notes": "list of strings: things to verify before substitution",
        }
        try:
            return await ai_client.chat_structured(
                [
                    {"role": "system", "content": PRODUCT_AGENT_SYSTEM},
                    {"role": "user", "content": substitute_prompt(product_info)},
                ],
                schema,
            )
        except Exception as e:
            logger.error(f"Substitute suggestion failed: {e}")
            return {"direct_substitutes": [], "functional_substitutes": [], "verification_notes": [f"AI分析失败: {e}"]}


WATCHTOWER_SYSTEM = """你是ERP系统的AI监控分析师。你需要扫描整个ERP系统的异常信号并生成预警报告。
请检测以下领域：
1. 库存风险：滞销库存、短缺风险、库存周转异常
2. 财务风险：逾期应收账款、现金流紧张、利润异常
3. 客户风险：客户流失信号、长期未联系客户、信用风险
4. 销售风险：商机流失、报价转化率下降、管道停滞
5. 供应链风险：供应商延迟、单一供应源、成本波动

对每个异常，给出严重程度（critical/high/medium/low）、摘要和影响描述。"""
