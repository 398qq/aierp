"""Brand profile generation."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.ai.client import ai_client
from app.services.ai.prompts import brand_profile_prompt
from app.services.brand_intel.context import _brand_context, _cached_brand_ai


async def generate_brand_profile(db: AsyncSession, brand_id: int) -> dict:
    """AI-generated brand intelligence card."""

    async def compute():
        ctx = await _brand_context(db, brand_id)

        schema = {
            "market_position": "string",
            "brand_strength_score": "integer 0-100",
            "technology_advantages": ["string"],
            "target_markets": ["string"],
            "competitive_advantages": ["string"],
            "typical_applications": ["string"],
            "key_competitors": ["string"],
            "procurement_difficulty": "string",
            "price_positioning": "string",
            "recommendation": "string",
        }
        result = await ai_client.chat_structured(
            [
                {
                    "role": "system",
                    "content": "你是一个电子元器件行业品牌分析专家，精通全球元器件品牌格局、市场定位和供应链分析。",
                },
                {"role": "user", "content": brand_profile_prompt(ctx)},
            ],
            schema,
        )
        result["context"] = ctx
        return result

    return await _cached_brand_ai(brand_id, "profile", compute, ttl=7200)
