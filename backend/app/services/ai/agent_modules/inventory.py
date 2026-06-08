"""InventoryAgent — AI inventory analysis.

Lightweight agent that interprets inventory snapshots and flags
low-stock or over-stock situations.
"""
from __future__ import annotations

import logging

from app.services.ai.client import ai_client
from app.services.ai.prompts import INVENTORY_AGENT_SYSTEM

logger = logging.getLogger(__name__)


class InventoryAgent:
    """Analyzes inventory data and provides stock recommendations."""

    @staticmethod
    async def analyze(inventory_data: list[dict]) -> dict:
        schema = {
            "urgent_purchases": "list of dicts: {product_name, current_stock, safety_stock, suggested_qty, reason}",
            "slow_moving": "list of dicts: {product_name, stock, days_untouched, suggestion}",
            "stockout_risks": "list of dicts: {product_name, current_stock, monthly_usage, months_remaining, suggestion}",
            "overall_assessment": "string",
        }
        try:
            import json
            data_text = json.dumps(inventory_data, ensure_ascii=False, default=str)
            result = await ai_client.chat_structured(
                [
                    {"role": "system", "content": INVENTORY_AGENT_SYSTEM},
                    {"role": "user", "content": f"分析以下库存数据，给出采购建议和预警：\n{data_text}"},
                ],
                schema,
            )
            return result
        except Exception as e:
            logger.error(f"Inventory analysis failed: {e}")
            return {
                "urgent_purchases": [],
                "slow_moving": [],
                "stockout_risks": [],
                "overall_assessment": f"AI分析暂时不可用: {e}",
            }


