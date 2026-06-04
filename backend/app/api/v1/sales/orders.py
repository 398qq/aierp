"""Sales API — sales order bounded context.

Routes for the sales order lifecycle:
- list / get / create / update / delete
- batch delete
- PDF generation
- PDF import (AI-extracted orders)

Cache invalidation also covers ``reports:predefined:sales`` since
sales order writes change the monthly aggregation.
"""

import io
import json
import logging

import sqlalchemy.orm
from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.api.v1.sales._shared import (
    SALES_ORDERS_LIST_CACHE_TTL,
    _sales_orders_cache_key,
)
from app.database import get_db
from app.schemas.common import fail, ok
from app.schemas.sales import (
    BatchDeleteRequest,
    SalesOrderCreate,
    SalesOrderUpdate,
)
from app.services import sales_service as svc
from app.services.cache_service import (
    cache_bump_version,
    cache_get_versioned,
    cache_set_versioned,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["sales:order"])


async def _bump_sales_order_caches() -> None:
    """Bump all caches affected by sales order writes."""
    await cache_bump_version("sales-orders:list")
    await cache_bump_version("dashboard:overview")
    await cache_bump_version("dashboard:kpi")
    await cache_bump_version("dashboard:trends")
    await cache_bump_version("reports:predefined:sales")


@router.get("/sales-orders")
async def list_sales_orders(
    response: JSONResponse,
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    customer_id: int | None = None, status: str | None = None,
    q: str | None = Query(None, description="Search customer, order no, notes, product line"),
    include_ai: bool = Query(False),
    sort_by: str = "id", sort_order: str = "desc",
    db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user),
):
    cache_key = _sales_orders_cache_key(
        page=page, page_size=page_size, customer_id=customer_id,
        status=status, q=q, sort_by=sort_by, sort_order=sort_order,
    )
    cached_payload = await cache_get_versioned('sales-orders:list', cache_key)
    if cached_payload is not None:
        result = json.loads(cached_payload)
        if include_ai and result.get("list"):
            from app.services.sales_ai_service import enrich_order_list
            ai_map = await enrich_order_list(db, result["list"])
            result["ai"] = ai_map
        response.headers["X-Cache"] = "HIT"
        response.headers["X-Cache-Key"] = cache_key
        return ok(result)

    response.headers["X-Cache"] = "MISS"
    result = await svc.list_sales_orders(
        db, page=page, page_size=page_size, customer_id=customer_id,
        status=status, q=q, sort_by=sort_by, sort_order=sort_order,
    )
    if include_ai and result["list"]:
        from app.services.sales_ai_service import enrich_order_list
        ai_map = await enrich_order_list(db, result["list"])
        result["ai"] = ai_map
    await cache_set_versioned('sales-orders:list', cache_key, json.dumps(result, default=str), SALES_ORDERS_LIST_CACHE_TTL)
    return ok(result)


@router.post("/sales-orders/import-pdf", status_code=status.HTTP_201_CREATED)
async def import_sales_order_pdf(
    customer_id: int | None = Query(None, description="客户无法从 PDF 识别时可手工指定"),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        return fail("请上传 PDF 订单文件")

    content = await file.read()
    if len(content) > 20 * 1024 * 1024:
        return fail("文件大小不能超过 20MB")

    try:
        from app.services.sales_order_pdf_import import import_sales_order_from_pdf
        result = await import_sales_order_from_pdf(
            db,
            content,
            filename=file.filename,
            customer_id=customer_id,
        )
        return ok(result, msg="PDF订单导入成功")
    except ValueError as e:
        return fail(str(e), 400)
    except Exception as e:
        return fail(f"PDF订单导入失败: {e}", 500)


@router.get("/sales-orders/{order_id}/pdf")
async def get_sales_order_pdf(
    order_id: int,
    template: str = Query("smart", description="smart | standard | compact"),
    company_name: str | None = Query(None, max_length=120),
    document_title: str | None = Query(None, max_length=120),
    show_smart_summary: bool = Query(True),
    show_line_hints: bool = Query(True),
    show_terms: bool = Query(True),
    show_notes: bool = Query(True),
    show_signature: bool = Query(True),
    prepared_by: str | None = Query(None, max_length=80),
    contact_phone: str | None = Query(None, max_length=60),
    terms: str | None = Query(None, max_length=2000),
    db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user),
):
    from app.models.customer import Customer
    from app.models.sales import SalesOrder

    result = await db.execute(
        select(SalesOrder)
        .where(SalesOrder.id == order_id, SalesOrder.deleted_at.is_(None))
        .options(sqlalchemy.orm.selectinload(SalesOrder.items))
    )
    order = result.scalar_one_or_none()
    if not order:
        return fail("销售订单不存在", 404)

    if order.customer_id:
        customer_result = await db.execute(select(Customer).where(Customer.id == order.customer_id))
        order.customer = customer_result.scalar_one_or_none()
    else:
        order.customer = None

    from app.services.pdf_service import generate_sales_order_pdf
    pdf_bytes = generate_sales_order_pdf(order, {
        "template": template,
        "company_name": company_name,
        "document_title": document_title,
        "show_smart_summary": show_smart_summary,
        "show_line_hints": show_line_hints,
        "show_terms": show_terms,
        "show_notes": show_notes,
        "show_signature": show_signature,
        "prepared_by": prepared_by,
        "contact_phone": contact_phone,
        "terms": terms,
    })

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="sales_order_{order.order_no or order_id}.pdf"'
        },
    )


@router.get("/sales-orders/{order_id}")
async def get_sales_order(
    order_id: int,
    include_ai: bool = Query(False),
    db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user),
):
    order = await svc.get_sales_order(db, order_id)
    if not order:
        return fail("销售订单不存在", 404)
    result = order
    if include_ai:
        from app.services.sales_ai_service import enrich_sales_order
        ai_data = await enrich_sales_order(db, order)
        from app.schemas.sales import SalesOrderResponse
        ai_result: dict = SalesOrderResponse.model_validate(order).model_dump()
        ai_result["ai"] = ai_data
        return ok(ai_result)
    return ok(order)


@router.post("/sales-orders", status_code=201)
async def create_sales_order(
    body: SalesOrderCreate,
    db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user),
):
    data = body.model_dump()
    items_data = data.pop("items", [])
    order = await svc.create_sales_order(db, data, items_data)
    await _bump_sales_order_caches()
    return ok(order)


@router.put("/sales-orders/{order_id}")
async def update_sales_order(
    order_id: int, body: SalesOrderUpdate,
    db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user),
):
    order = await svc.get_sales_order(db, order_id)
    if not order:
        return fail("销售订单不存在", 404)
    order = await svc.update_sales_order(db, order, body.model_dump(exclude_none=True))
    await _bump_sales_order_caches()
    return ok(order)


@router.delete("/sales-orders/{order_id}")
async def delete_sales_order(
    order_id: int,
    db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user),
):
    order = await svc.get_sales_order(db, order_id)
    if not order:
        return fail("销售订单不存在", 404)
    await svc.delete_sales_order(db, order)
    await _bump_sales_order_caches()
    return ok({"deleted": order_id})


@router.post("/sales-orders/batch-delete")
async def batch_delete_sales_orders(
    body: BatchDeleteRequest,
    db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user),
):
    for oid in body.ids:
        order = await svc.get_sales_order(db, oid)
        if order:
            await svc.delete_sales_order(db, order)
    await _bump_sales_order_caches()
    return ok({"deleted": len(body.ids)})
