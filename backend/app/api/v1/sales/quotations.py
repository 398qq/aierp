"""Sales API — quotation bounded context.

Routes for the quotation lifecycle:
- list / stats / get / create / update / delete
- duplicate / status / send
- PDF generation
- creation from inquiry
- batch delete

AI enrichment and pipeline hooks live in
``app.services.sales_ai_service`` and ``app.services.sales_ai_pipeline``.
"""

import io
import json
import logging

import sqlalchemy.orm
from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.api.v1.sales._shared import (
    QUOTATIONS_LIST_CACHE_TTL,
    QUOTATIONS_STATS_CACHE_TTL,
    _quotations_cache_key,
)
from app.database import get_db
from app.schemas.common import fail, ok
from app.schemas.sales import (
    BatchDeleteRequest,
    QuotationCreate,
    QuotationFromInquiryRequest,
    QuotationStatusUpdate,
    QuotationUpdate,
)
from app.services import sales_service as svc
from app.services.cache_service import (
    cache_bump_version,
    cache_get_versioned,
    cache_set_versioned,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["sales:quotation"])


async def _bump_quotation_caches() -> None:
    """Bump all caches affected by quotation writes."""
    await cache_bump_version("quotations:list")
    await cache_bump_version("quotations:stats")
    await cache_bump_version("dashboard:overview")
    await cache_bump_version("dashboard:kpi")
    await cache_bump_version("reports:predefined:sales")


@router.get("/quotations")
async def list_quotations(
    response: JSONResponse,
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    customer_id: int | None = None, status: str | None = None,
    q: str | None = Query(None, description="Search customer, quotation no, title, notes, product line"),
    include_ai: bool = Query(False),
    sort_by: str = "id", sort_order: str = "desc",
    db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user),
):
    cache_key = _quotations_cache_key(
        page=page, page_size=page_size, customer_id=customer_id,
        status=status, q=q, sort_by=sort_by, sort_order=sort_order,
    )
    cached_payload = await cache_get_versioned('quotations:list', cache_key)
    if cached_payload is not None:
        result = json.loads(cached_payload)
        if include_ai and result.get("list"):
            from app.services.sales_ai_service import enrich_quotation_list
            ai_map = await enrich_quotation_list(db, result["list"])
            result["ai"] = ai_map
        response.headers["X-Cache"] = "HIT"
        response.headers["X-Cache-Key"] = cache_key
        return ok(result)

    response.headers["X-Cache"] = "MISS"
    result = await svc.list_quotations(
        db, page=page, page_size=page_size, customer_id=customer_id,
        status=status, q=q, sort_by=sort_by, sort_order=sort_order,
    )
    if include_ai and result["list"]:
        from app.services.sales_ai_service import enrich_quotation_list
        ai_map = await enrich_quotation_list(db, result["list"])
        result["ai"] = ai_map
    await cache_set_versioned('quotations:list', cache_key, json.dumps(result, default=str), QUOTATIONS_LIST_CACHE_TTL)
    return ok(result)


@router.get("/quotations/stats")
async def quotation_stats(
    response: JSONResponse,
    db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user),
):
    cache_key = "quotations:stats:global"
    cached_payload = await cache_get_versioned("quotations:stats", cache_key)
    if cached_payload is not None:
        response.headers["X-Cache"] = "HIT"
        response.headers["X-Cache-Key"] = cache_key
        return ok(json.loads(cached_payload))
    response.headers["X-Cache"] = "MISS"
    result = await svc.get_quotation_stats(db)
    await cache_set_versioned(
        "quotations:stats", cache_key,
        json.dumps(result, default=str), QUOTATIONS_STATS_CACHE_TTL,
    )
    return ok(result)


@router.get("/quotations/{quote_id}")
async def get_quotation(
    quote_id: int,
    include_ai: bool = Query(False),
    db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user),
):
    quote = await svc.get_quotation(db, quote_id)
    if not quote:
        return fail("报价单不存在", 404)
    result = quote
    if include_ai:
        from app.services.sales_ai_service import enrich_quotation
        ai_data = await enrich_quotation(db, quote)
        from app.schemas.sales import QuotationResponse
        result = QuotationResponse.model_validate(quote).model_dump()
        result["ai"] = ai_data
        return ok(result)
    return ok(quote)


@router.post("/quotations/{quote_id}/duplicate", status_code=201)
async def duplicate_quotation(
    quote_id: int,
    db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user),
):
    quote = await svc.get_quotation(db, quote_id)
    if not quote:
        return fail("报价单不存在", 404)
    duplicated = await svc.duplicate_quotation(db, quote)
    await _bump_quotation_caches()
    return ok(duplicated)


@router.put("/quotations/{quote_id}/status")
async def update_quotation_status(
    quote_id: int,
    body: QuotationStatusUpdate,
    db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user),
):
    quote = await svc.get_quotation(db, quote_id)
    if not quote:
        return fail("报价单不存在", 404)
    try:
        quote = await svc.update_quotation_status(db, quote, body.status)
    except ValueError as e:
        return fail(str(e), 400)
    await _bump_quotation_caches()
    return ok(quote)


@router.get("/quotations/{quote_id}/pdf")
async def get_quotation_pdf(
    quote_id: int,
    template: str = Query("smart", description="smart | standard | compact"),
    company_name: str | None = Query(None, max_length=120),
    document_title: str | None = Query(None, max_length=120),
    show_smart_summary: bool = Query(True),
    show_line_hints: bool = Query(True),
    show_terms: bool = Query(True),
    show_notes: bool = Query(True),
    show_internal_metrics: bool = Query(False),
    show_signature: bool = Query(True),
    prepared_by: str | None = Query(None, max_length=80),
    contact_phone: str | None = Query(None, max_length=60),
    terms: str | None = Query(None, max_length=2000),
    db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user),
):
    from app.models.sales import Quotation
    from app.models.customer import Customer
    result = await db.execute(
        select(Quotation)
        .where(Quotation.id == quote_id)
        .options(sqlalchemy.orm.selectinload(Quotation.items))
    )
    quote = result.scalar_one_or_none()
    if not quote:
        return fail("报价单不存在", 404)

    if quote.customer_id:
        customer_result = await db.execute(
            select(Customer).where(Customer.id == quote.customer_id)
        )
        quote.customer = customer_result.scalar_one_or_none()
    else:
        quote.customer = None

    from app.services.pdf_service import generate_quotation_pdf
    pdf_bytes = generate_quotation_pdf(quote, {
        "template": template,
        "company_name": company_name,
        "document_title": document_title,
        "show_smart_summary": show_smart_summary,
        "show_line_hints": show_line_hints,
        "show_terms": show_terms,
        "show_notes": show_notes,
        "show_internal_metrics": show_internal_metrics,
        "show_signature": show_signature,
        "prepared_by": prepared_by,
        "contact_phone": contact_phone,
        "terms": terms,
    })

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="quotation_{quote.quotation_no or quote_id}.pdf"'
        }
    )


@router.post("/quotations", status_code=201)
async def create_quotation(
    body: QuotationCreate,
    db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user),
):
    data = body.model_dump()
    items_data = data.pop("items", [])
    quote = await svc.create_quotation(db, data, items_data)
    from app.services.sales_ai_pipeline import after_quotation_save
    after_quotation_save(quote.id)
    await _bump_quotation_caches()
    return ok(quote)


@router.put("/quotations/{quote_id}")
async def update_quotation(
    quote_id: int, body: QuotationUpdate,
    db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user),
):
    quote = await svc.get_quotation(db, quote_id)
    if not quote:
        return fail("报价单不存在", 404)
    data = body.model_dump(exclude_none=True)
    if body.items is not None:
        data["items"] = body.items
    quote = await svc.update_quotation(db, quote, data)
    from app.services.sales_ai_pipeline import after_quotation_save
    after_quotation_save(quote.id)
    await _bump_quotation_caches()
    return ok(quote)


@router.delete("/quotations/{quote_id}")
async def delete_quotation(
    quote_id: int,
    db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user),
):
    quote = await svc.get_quotation(db, quote_id)
    if not quote:
        return fail("报价单不存在", 404)
    await svc.delete_quotation(db, quote)
    await _bump_quotation_caches()
    return ok({"deleted": quote_id})


@router.post("/quotations/batch-delete")
async def batch_delete_quotations(
    body: BatchDeleteRequest,
    db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user),
):
    for qid in body.ids:
        quote = await svc.get_quotation(db, qid)
        if quote:
            await svc.delete_quotation(db, quote)
    await _bump_quotation_caches()
    return ok({"deleted": len(body.ids)})


@router.put("/quotations/{quote_id}/send")
async def send_quotation(
    quote_id: int,
    db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user),
):
    quote = await svc.get_quotation(db, quote_id)
    if not quote:
        return fail("报价单不存在", 404)
    quote = await svc.send_quotation(db, quote)
    await _bump_quotation_caches()
    return ok(quote)


@router.post("/quotations/from-inquiry", status_code=201)
async def create_quotation_from_inquiry(
    body: QuotationFromInquiryRequest,
    db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user),
):
    try:
        quote = await svc.create_quotation_from_inquiry(
            db,
            inquiry_id=body.inquiry_id,
            customer_id=body.customer_id,
            title=body.title,
            valid_until=body.valid_until,
            notes=body.notes,
            items=body.items,
        )
        await _bump_quotation_caches()
        return ok({"id": quote.id, "quotation_no": quote.quotation_no})
    except ValueError as e:
        return fail(str(e), 400)
    except Exception as e:
        return fail(f"创建失败: {e}", 500)
