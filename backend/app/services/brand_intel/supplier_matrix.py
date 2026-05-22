"""Brand-supplier matrix analysis."""

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product, Supplier, SupplierProduct
from app.services.ai.client import ai_client
from app.services.ai.prompts import brand_supplier_matrix_prompt
from app.services.brand_intel.context import _brand_context


async def get_brand_supplier_matrix(db: AsyncSession, brand_id: int) -> dict:
    """Supplier coverage, pricing comparison, single-source detection for a brand."""
    ctx = await _brand_context(db, brand_id)

    product_ids = [r[0] for r in (
        await db.execute(
            select(Product.id).where(
                Product.brand_id == brand_id, Product.deleted_at.is_(None)
            )
        )
    ).all()]

    supplier_rows = (await db.execute(
        select(
            Supplier.id, Supplier.name,
            func.count(SupplierProduct.product_id).label('pc'),
            func.avg(SupplierProduct.cost_price).label('avg_cost'),
            func.min(SupplierProduct.cost_price).label('min_cost'),
            func.max(SupplierProduct.cost_price).label('max_cost'),
            func.avg(SupplierProduct.lead_time_days).label('avg_lt'),
            func.min(SupplierProduct.lead_time_days).label('min_lt'),
            func.max(SupplierProduct.lead_time_days).label('max_lt'),
        )
        .select_from(Supplier)
        .join(SupplierProduct, Supplier.id == SupplierProduct.supplier_id)
        .where(
            SupplierProduct.product_id.in_(product_ids),
            SupplierProduct.deleted_at.is_(None),
            Supplier.deleted_at.is_(None),
        )
        .group_by(Supplier.id)
        .order_by(text('pc DESC'))
    )).all()

    supplier_details = []
    for r in supplier_rows:
        supplier_details.append({
            "supplier_id": r[0],
            "supplier_name": r[1],
            "product_count": r[2],
            "avg_cost": float(r[3]) if r[3] else None,
            "min_cost": float(r[4]) if r[4] else None,
            "max_cost": float(r[5]) if r[5] else None,
            "avg_lead_time": round(float(r[6]), 1) if r[6] else None,
            "min_lead_time": r[7],
            "max_lead_time": r[8],
        })

    supplier_price_ranking = ", ".join(
        f"{s['supplier_name']}: ¥{s['avg_cost']:.4f}" if s['avg_cost'] else f"{s['supplier_name']}: 暂无报价"
        for s in sorted(supplier_details, key=lambda x: x['avg_cost'] or 999999)
    ) if supplier_details else "无数据"

    supplier_count_per_product = (await db.execute(
        select(
            func.count(SupplierProduct.supplier_id).label('sc'),
        ).where(
            SupplierProduct.product_id.in_(product_ids),
            SupplierProduct.deleted_at.is_(None),
        ).group_by(SupplierProduct.product_id)
    )).all()

    products_with_backup = sum(1 for r in supplier_count_per_product if r[0] >= 2)
    backup_pct = round(products_with_backup / len(product_ids) * 100, 1) if product_ids else 0

    lt_rows = [s['avg_lead_time'] for s in supplier_details if s['avg_lead_time']]
    avg_lt = round(sum(lt_rows) / len(lt_rows), 1) if lt_rows else None
    lt_range = f"{min(lt_rows)}~{max(lt_rows)}天" if lt_rows else "无数据"

    matrix_data = {
        **ctx,
        "supplier_details": ", ".join(
            f"{s['supplier_name']}({s['product_count']}个产品, 均价¥{s['avg_cost']:.4f}, 交期{s['avg_lead_time']}天)"
            if s['avg_cost'] and s['avg_lead_time']
            else f"{s['supplier_name']}({s['product_count']}个产品)"
            for s in supplier_details
        ) if supplier_details else "无",
        "avg_products_per_supplier": round(ctx.get("product_count", 0) / max(len(supplier_details), 1), 1),
        "backup_coverage_pct": backup_pct,
        "supplier_price_ranking": supplier_price_ranking,
        "avg_lead_time": avg_lt,
        "lead_time_range": lt_range,
    }

    schema = {
        "overall_assessment": "string",
        "coverage_score": "integer 0-100",
        "single_source_products": [
            {"product_name": "string", "supplier": "string", "cost_price": "number", "risk_reason": "string"}
        ],
        "backup_recommendations": [
            {"current": "string", "recommended": "string", "reason": "string"}
        ],
        "price_optimization": ["string"],
        "negotiation_leverage": "string",
    }
    result = await ai_client.chat_structured(
        [{"role": "system", "content": "你是一个电子元器件采购策略专家，擅长供应商矩阵分析和采购优化。"},
         {"role": "user", "content": brand_supplier_matrix_prompt(matrix_data)}],
        schema,
    )
    result["context"] = matrix_data
    result["supplier_details"] = supplier_details
    return result