"""Brand import from text."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Brand
from app.services.ai.client import ai_client
from app.services.ai.prompts import brand_import_prompt


async def import_brand_from_text(
    db: AsyncSession, text: str, auto_create: bool = False
) -> dict:
    """AI extracts structured brand info from free text."""
    schema = {
        "name": "string: brand English name",
        "name_cn": "string | null",
        "category": "string: main product category",
        "website": "string | null",
        "description": "string: 1-2 sentence intro",
        "product_lines": "string: main product lines",
    }
    result = await ai_client.chat_structured(
        [
            {
                "role": "system",
                "content": "你是一个电子元器件数据专家，精确提取品牌信息。",
            },
            {"role": "user", "content": brand_import_prompt(text)},
        ],
        schema,
    )

    if auto_create and result.get("name"):
        existing = (
            await db.execute(
                select(Brand).where(
                    Brand.name == result["name"], Brand.deleted_at.is_(None)
                )
            )
        ).scalar_one_or_none()
        if not existing:
            brand = Brand(
                name=result["name"],
                name_cn=result.get("name_cn"),
                category=result.get("category"),
                website=result.get("website"),
                notes=result.get("description"),
            )
            db.add(brand)
            await db.flush()
            result["created_id"] = brand.id

    return result
