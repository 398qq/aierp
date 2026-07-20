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
from decimal import Decimal

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
from app.models.sales import Quotation
from app.schemas.common import fail, ok, APIResponse, PageData
from app.schemas.sales import (
    QuotationResponse,
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


async def _reload_quotation_for_serialize(db: AsyncSession, quote_id: int) -> dict:
    """Re-fetch a Quotation with customer + opportunity + items eagerly loaded,
    so the response can include `customer_name` and the items list without
    triggering async lazy-loads.

    The project's aiosqlite test setup doesn't support async lazy loading
    (see conftest note), so we explicitly assign related objects to the
    ORM instance — matching the pattern used by the PDF endpoint.
    """
    from app.models.customer import Customer
    from app.models.sales import Opportunity, QuotationItem

    quote_result = await db.execute(
        select(Quotation).where(
            Quotation.id == quote_id, Quotation.deleted_at.is_(None)
        )
    )
    quote = quote_result.scalar_one_or_none()
    if not quote:
        return {}
    # Eager-load related entities
    if quote.customer_id:
        cust = (
            await db.execute(select(Customer).where(Customer.id == quote.customer_id))
        ).scalar_one_or_none()
        quote.customer = cust
    else:
        quote.customer = None
    if quote.opportunity_id:
        opp = (
            await db.execute(
                select(Opportunity).where(Opportunity.id == quote.opportunity_id)
            )
        ).scalar_one_or_none()
        quote.opportunity = opp
    else:
        quote.opportunity = None
    items_result = await db.execute(
        select(QuotationItem).where(
            QuotationItem.quotation_id == quote.id, QuotationItem.deleted_at.is_(None)
        )
    )
    quote.items = list(items_result.scalars().all())
    return _serialize_quotation(quote)


def _serialize_quotations(quotes: list) -> list[dict]:
    """Serialize a list of Quotation ORM objects to JSON-safe dicts.

    Assumes the caller has already eager-loaded customer, opportunity, and
    items on each Quotation (via joinedload). If not, the missing attributes
    will be `None` in the output.
    """
    return [_serialize_quotation(q) for q in quotes]


async def _bump_quotation_caches() -> None:
    """Bump all caches affected by quotation writes."""
    await cache_bump_version("quotations:list")
    await cache_bump_version("quotations:stats")
    await cache_bump_version("dashboard:overview")
    await cache_bump_version("dashboard:kpi")
    await cache_bump_version("reports:predefined:sales")


def _serialize_quotation(quote) -> dict:
    """Convert a Quotation ORM to a JSON-safe dict with denormalized customer_name.

    Avoids the N+1 problem: the caller must `selectinload(Quotation.customer)`
    and `selectinload(Quotation.opportunity)` before invoking this.
    """
    return {
        "id": quote.id,
        "quotation_no": quote.quotation_no,
        "customer_id": quote.customer_id,
        "customer_name": quote.customer.name if quote.customer else None,
        "opportunity_id": quote.opportunity_id,
        "opportunity_title": quote.opportunity.title if quote.opportunity else None,
        "title": quote.title,
        "total_amount": float(Decimal(str(quote.total_amount or 0))),
        "status": quote.status,
        "currency": quote.currency,
        "incoterms": quote.incoterms,
        "payment_terms": quote.payment_terms,
        "discount_rate": float(quote.discount_rate) if quote.discount_rate else None,
        "discount_amount": float(Decimal(str(quote.discount_amount)))
        if quote.discount_amount is not None
        else None,
        "subtotal": float(Decimal(str(quote.subtotal)))
        if quote.subtotal is not None
        else None,
        "valid_until": quote.valid_until.isoformat() if quote.valid_until else None,
        "notes": quote.notes,
        "created_at": quote.created_at.isoformat() if quote.created_at else None,
        "updated_at": quote.updated_at.isoformat() if quote.updated_at else None,
        "items": [
            {
                "id": it.id,
                "quotation_id": it.quotation_id,
                "product_id": it.product_id,
                "product_name": it.product_name,
                "customer_part_no": it.customer_part_no,
                "customer_product_name": it.customer_product_name,
                "quantity": it.quantity,
                "unit": it.unit,
                "unit_price": float(Decimal(str(it.unit_price)))
                if it.unit_price is not None
                else None,
                "total_price": float(Decimal(str(it.total_price)))
                if it.total_price is not None
                else None,
                "tax_rate": float(it.tax_rate) if it.tax_rate else None,
                "discount_rate": float(it.discount_rate) if it.discount_rate else None,
                "cost_price": float(Decimal(str(it.cost_price)))
                if it.cost_price is not None
                else None,
                "untaxed_cost": float(it.untaxed_cost)
                if it.untaxed_cost is not None
                else None,
                "taxed_cost": float(it.taxed_cost)
                if it.taxed_cost is not None
                else None,
                "sales_profit": float(it.sales_profit)
                if it.sales_profit is not None
                else None,
                "datecode": it.datecode,
                "lead_time": it.lead_time,
                "notes": it.notes,
            }
            for it in (quote.items or [])
        ],
    }


@router.get("/quotations", response_model=APIResponse[PageData[QuotationResponse]])
async def list_quotations(
    response: JSONResponse,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    customer_id: int | None = None,
    status: str | None = None,
    q: str | None = Query(
        None, description="Search customer, quotation no, title, notes, product line"
    ),
    include_ai: bool = Query(False),
    sort_by: str = "id",
    sort_order: str = "desc",
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    cache_key = _quotations_cache_key(
        page=page,
        page_size=page_size,
        customer_id=customer_id,
        status=status,
        q=q,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    cached_payload = await cache_get_versioned("quotations:list", cache_key)
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
    raw = await svc.list_quotations(
        db,
        page=page,
        page_size=page_size,
        customer_id=customer_id,
        status=status,
        q=q,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    # Eager-load customer + opportunity + items on every Quotation in the
    # page so the response can include customer_name without triggering
    # async lazy-loads. We use a separate IN query instead of joinedload
    # to avoid cartesian explosion on large pages.
    from app.models.customer import Customer
    from app.models.sales import Opportunity, Quotation, QuotationItem
    from typing import cast

    quotes = cast(list[Quotation], list(raw["list"]))
    custs: dict[int, Customer] = {}
    opps: dict[int, Opportunity] = {}
    if quotes:
        quote_ids = [q.id for q in quotes]
        cust_ids = list({q.customer_id for q in quotes if q.customer_id})
        opp_ids = list({q.opportunity_id for q in quotes if q.opportunity_id})
        items_by_q: dict[int, list[QuotationItem]] = {qid: [] for qid in quote_ids}
        if cust_ids:
            cust_rows = (
                (await db.execute(select(Customer).where(Customer.id.in_(cust_ids))))
                .scalars()
                .all()
            )
            custs = {c.id: c for c in cust_rows}
        if opp_ids:
            opp_rows = (
                (
                    await db.execute(
                        select(Opportunity).where(Opportunity.id.in_(opp_ids))
                    )
                )
                .scalars()
                .all()
            )
            opps = {o.id: o for o in opp_rows}
        item_rows = (
            (
                await db.execute(
                    select(QuotationItem).where(
                        QuotationItem.quotation_id.in_(quote_ids),
                        QuotationItem.deleted_at.is_(None),
                    )
                )
            )
            .scalars()
            .all()
        )
        for it in item_rows:
            items_by_q.setdefault(it.quotation_id, []).append(it)
        for q in quotes:  # type: ignore[union-attr,assignment]
            # Only assign non-None to many-to-one relationships to avoid
            # clearing NOT NULL FK columns when the related row is missing.
            if (c := custs.get(q.customer_id)) is not None:  # type: ignore[union-attr]
                q.customer = c  # type: ignore[union-attr]
            if (o := opps.get(q.opportunity_id)) is not None:  # type: ignore[union-attr]
                q.opportunity = o  # type: ignore[union-attr]
            q.items = items_by_q.get(q.id, [])  # type: ignore[union-attr]
    serialized_list = _serialize_quotations(quotes)
    result = {**raw, "list": serialized_list}
    if include_ai and result["list"]:
        # enrich_quotation_list expects ORM objects; pass quotes
        from app.services.sales_ai_service import enrich_quotation_list

        ai_map = await enrich_quotation_list(db, quotes)
        result["ai"] = ai_map
    await cache_set_versioned(
        "quotations:list", cache_key, json.dumps(result), QUOTATIONS_LIST_CACHE_TTL
    )
    return ok(result)


@router.get("/quotations/stats")
async def quotation_stats(
    response: JSONResponse,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
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
        "quotations:stats",
        cache_key,
        json.dumps(result, default=str),
        QUOTATIONS_STATS_CACHE_TTL,
    )
    return ok(result)


@router.get("/quotations/{quote_id}", response_model=APIResponse[QuotationResponse])
async def get_quotation(
    quote_id: int,
    include_ai: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    quote = await svc.get_quotation(db, quote_id)
    if not quote:
        return fail("报价单不存在", 404)
    if include_ai:
        from app.services.sales_ai_service import enrich_quotation

        ai_data = await enrich_quotation(db, quote)
        from app.schemas.sales import QuotationResponse

        ai_result: dict = QuotationResponse.model_validate(quote).model_dump()
        ai_result["ai"] = ai_data
        return ok(ai_result)
    return ok(await _reload_quotation_for_serialize(db, quote.id))


@router.post("/quotations/{quote_id}/duplicate", status_code=201)
async def duplicate_quotation(
    quote_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
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
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    quote = await svc.get_quotation(db, quote_id)
    if not quote:
        return fail("报价单不存在", 404)
    try:
        quote = await svc.update_quotation_status(db, quote, body.status)
    except ValueError as e:
        return fail(str(e), 400)
    await _bump_quotation_caches()
    return ok(await _reload_quotation_for_serialize(db, quote.id))


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
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
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

    pdf_bytes = generate_quotation_pdf(
        quote,
        {
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
        },
    )

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="QUOTATION_{quote.quotation_no or quote_id}.pdf"'
        },
    )


@router.post(
    "/quotations", status_code=201, response_model=APIResponse[QuotationResponse]
)
async def create_quotation(
    body: QuotationCreate,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    data = body.model_dump()
    items_data = data.pop("items", [])
    quote = await svc.create_quotation(db, data, items_data)
    from app.services.sales_ai_pipeline import after_quotation_save

    after_quotation_save(quote.id)
    await _bump_quotation_caches()
    return ok(await _reload_quotation_for_serialize(db, quote.id))


@router.put("/quotations/{quote_id}", response_model=APIResponse[QuotationResponse])
async def update_quotation(
    quote_id: int,
    body: QuotationUpdate,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
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
    return ok(await _reload_quotation_for_serialize(db, quote.id))


@router.delete("/quotations/{quote_id}")
async def delete_quotation(
    quote_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
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
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
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
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    quote = await svc.get_quotation(db, quote_id)
    if not quote:
        return fail("报价单不存在", 404)
    quote = await svc.send_quotation(db, quote)
    await _bump_quotation_caches()
    return ok(await _reload_quotation_for_serialize(db, quote.id))


@router.post("/quotations/from-inquiry", status_code=201)
async def create_quotation_from_inquiry(
    body: QuotationFromInquiryRequest,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
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
