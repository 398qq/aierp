"""Brand portfolio analysis."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.ai.client import ai_client
from app.services.ai.prompts import brand_portfolio_prompt
from app.services.brand_intel.context import _brand_context, _cached_brand_ai


async def analyze_brand_portfolio(db: AsyncSession, brand_id: int) -> dict:
    """AI analysis of brand product portfolio."""

    async def compute():
        ctx = await _brand_context(db, brand_id)

        schema = {
            "portfolio_strength": "string: 完整/较全/聚焦/单一",
            "category_analysis": [
                {
                    "category": "string",
                    "count": "integer",
                    "pct": "number",
                    "assessment": "string",
                }
            ],
            "growth_areas": ["string"],
            "gap_analysis": ["string"],
            "cross_sell_opportunities": ["string"],
            "inventory_health": "string",
        }
        result = await ai_client.chat_structured(
            [
                {
                    "role": "system",
                    "content": "你是一个电子元器件产品线管理专家，擅长产品组合分析和市场策略。",
                },
                {"role": "user", "content": brand_portfolio_prompt(ctx)},
            ],
            schema,
        )
        result["context"] = ctx
        return result

    return await _cached_brand_ai(brand_id, "portfolio", compute, ttl=7200)
