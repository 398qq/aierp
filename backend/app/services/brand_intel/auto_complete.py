"""Brand auto-completion using AI."""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Brand
from app.services.ai.client import ai_client

logger = logging.getLogger(__name__)


async def auto_complete_brand(db: AsyncSession, brand_id: int) -> dict:
    """AI auto-completes missing brand fields based on existing data and industry knowledge."""
    brand = (await db.execute(
        select(Brand).where(Brand.id == brand_id, Brand.deleted_at.is_(None))
    )).scalar_one_or_none()
    if brand is None:
        raise ValueError("Brand not found")

    existing = {
        "name": brand.name, "name_cn": brand.name_cn, "short_name": brand.short_name,
        "code": brand.code, "brand_type": brand.brand_type, "status": brand.status,
        "category": brand.category, "description": brand.description,
        "level": brand.level, "positioning": brand.positioning, "owner": brand.owner,
        "product_lines": brand.product_lines, "target_markets": brand.target_markets,
        "website": brand.website,
        "manufacturer_name": brand.manufacturer_name, "authorization_status": brand.authorization_status,
        "lifecycle_stage": brand.lifecycle_stage, "is_automotive": brand.is_automotive,
        "moq": brand.moq, "lead_time_days": brand.lead_time_days,
        "risk_level": brand.risk_level, "rohs_status": brand.rohs_status,
        "ai_keywords": brand.ai_keywords, "risk_score": brand.risk_score,
        "alternative_brands": brand.alternative_brands,
    }

    missing_fields = [k for k, v in existing.items() if v is None and k not in ("short_name", "logo")]

    if not missing_fields:
        return {"brand_id": brand_id, "filled": {}, "message": "所有字段已完整，无需补全"}

    prompt = f"""你是电子元器件品牌数据专家。根据你对 {existing['name']} ({existing.get('name_cn', '')}) 的了解，补全以下字段。

已知信息：{existing['name']} 是 {existing.get('category', '未知品类')} 领域的品牌{existing.get('description', '')}。

请用以下格式逐行返回（只返回需要补全的字段，一行一个）：
{chr(10).join(f'{f}: <值>' for f in missing_fields)}

规则：
- 所有信息必须基于真实行业知识
- 不确定的填"未知"
- 数值字段只填数字
- 多个值之间必须用逗号分隔，不要用其他符号
- risk_score: 0-100整数，综合缺货/停产/交期风险"""

    try:
        text_out = await ai_client.chat(
            [{"role": "system", "content": "你是电子元器件行业专家。只返回指定格式的数据，不要解释。"},
             {"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=1024,
        )

        filled = {}
        for line in text_out.strip().split("\n"):
            line = line.strip()
            if ":" not in line:
                continue
            key, _, val = line.partition(":")
            key = key.strip().lower()
            val = val.strip()
            if key in missing_fields and val and val not in ("None", "none", "null", "未知", "无", "-"):
                filled[key] = val
                if key == "risk_score":
                    try:
                        setattr(brand, key, float(val))
                    except (ValueError, TypeError):
                        pass
                elif key == "moq":
                    try:
                        setattr(brand, key, int(float(val)))
                    except (ValueError, TypeError):
                        pass
                elif key == "lead_time_days":
                    try:
                        setattr(brand, key, int(float(val)))
                    except (ValueError, TypeError):
                        pass
                elif key == "is_automotive":
                    setattr(brand, key, val.lower() in ("true", "yes", "是", "1"))
                else:
                    setattr(brand, key, val)

        await db.flush()

        return {
            "brand_id": brand_id,
            "filled": filled,
            "message": f"已补全 {len(filled)} 个字段" if filled else "AI 未能补全任何字段，可能是缺失字段信息不足",
        }

    except Exception as e:
        logger.error(f"auto_complete_brand failed: {e}")
        raise