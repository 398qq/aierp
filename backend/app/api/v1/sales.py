"""Sales API — opportunities, quotations, orders, delivery notes with AI enrichment."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.schemas.common import fail, ok
from app.schemas.sales import (
    DeliveryNoteCreate, DeliveryNoteUpdate,
    OpportunityCreate, OpportunityUpdate,
    QuotationCreate, QuotationUpdate,
    SalesOrderCreate, SalesOrderUpdate,
    BatchDeleteRequest, OpportunityBatchUpdate, ConversionValidation, ConvertResponse,
)
from app.services import sales_service as svc

router = APIRouter(tags=["sales"])


# ============================================================
# Opportunity
# ============================================================

@router.get("/opportunities")
async def list_opportunities(
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    customer_id: int | None = None, status: str | None = None,
    stage: str | None = None, assigned_to: str | None = None,
    include_ai: bool = Query(False),
    sort_by: str = "id", sort_order: str = "desc",
    db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user),
):
    result = await svc.list_opportunities(
        db, page=page, page_size=page_size, customer_id=customer_id,
        status=status, stage=stage, assigned_to=assigned_to,
        sort_by=sort_by, sort_order=sort_order,
    )
    if include_ai and result["list"]:
        from app.services.sales_ai_service import enrich_opportunity_list
        ai_map = await enrich_opportunity_list(db, result["list"])
        result["ai"] = ai_map
    return ok(result)


@router.get("/opportunities/{opp_id}")
async def get_opportunity(
    opp_id: int,
    include_ai: bool = Query(False),
    db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user),
):
    opp = await svc.get_opportunity(db, opp_id)
    if not opp:
        return fail("商机不存在", 404)
    result = opp
    if include_ai:
        from app.services.sales_ai_service import enrich_opportunity
        ai_data = await enrich_opportunity(db, opp)
        result = {**opp.__dict__, "ai": ai_data}
    return ok(result)


@router.post("/opportunities", status_code=201)
async def create_opportunity(
    body: OpportunityCreate,
    db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user),
):
    opp = await svc.create_opportunity(db, body.model_dump())
    from app.services.sales_ai_pipeline import after_opportunity_save
    after_opportunity_save(opp.id)
    return ok(opp)


@router.put("/opportunities/{opp_id}")
async def update_opportunity(
    opp_id: int, body: OpportunityUpdate,
    db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user),
):
    opp = await svc.get_opportunity(db, opp_id)
    if not opp:
        return fail("商机不存在", 404)
    opp = await svc.update_opportunity(db, opp, body.model_dump(exclude_none=True))
    from app.services.sales_ai_pipeline import after_opportunity_save
    after_opportunity_save(opp.id)
    return ok(opp)


@router.delete("/opportunities/{opp_id}")
async def delete_opportunity(
    opp_id: int,
    db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user),
):
    opp = await svc.get_opportunity(db, opp_id)
    if not opp:
        return fail("商机不存在", 404)
    await svc.delete_opportunity(db, opp)
    return ok({"deleted": opp_id})


@router.post("/opportunities/batch-delete")
async def batch_delete_opportunities(
    body: BatchDeleteRequest,
    db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user),
):
    for oid in body.ids:
        opp = await svc.get_opportunity(db, oid)
        if opp:
            await svc.delete_opportunity(db, opp)
    return ok({"deleted": len(body.ids)})


@router.post("/opportunities/batch-update")
async def batch_update_opportunities(
    body: OpportunityBatchUpdate,
    db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user),
):
    count = 0
    for oid in body.ids:
        opp = await svc.get_opportunity(db, oid)
        if opp:
            updates = {}
            if body.stage is not None:
                updates["stage"] = body.stage
            if body.win_probability is not None:
                updates["win_probability"] = body.win_probability
            if updates:
                await svc.update_opportunity(db, opp, updates)
                count += 1
    return ok({"updated": count})


# ============================================================
# Quotation
# ============================================================

@router.get("/quotations")
async def list_quotations(
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    customer_id: int | None = None, status: str | None = None,
    include_ai: bool = Query(False),
    sort_by: str = "id", sort_order: str = "desc",
    db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user),
):
    result = await svc.list_quotations(
        db, page=page, page_size=page_size, customer_id=customer_id,
        status=status, sort_by=sort_by, sort_order=sort_order,
    )
    if include_ai and result["list"]:
        from app.services.sales_ai_service import enrich_quotation_list
        ai_map = await enrich_quotation_list(db, result["list"])
        result["ai"] = ai_map
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
        result = {**quote.__dict__, "ai": ai_data}
    return ok(result)


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
    return ok(quote)


@router.put("/quotations/{quote_id}")
async def update_quotation(
    quote_id: int, body: QuotationUpdate,
    db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user),
):
    quote = await svc.get_quotation(db, quote_id)
    if not quote:
        return fail("报价单不存在", 404)
    quote = await svc.update_quotation(db, quote, body.model_dump(exclude_none=True))
    from app.services.sales_ai_pipeline import after_quotation_save
    after_quotation_save(quote.id)
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
    return ok({"deleted": len(body.ids)})


# ============================================================
# Sales Order
# ============================================================

@router.get("/sales-orders")
async def list_sales_orders(
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    customer_id: int | None = None, status: str | None = None,
    include_ai: bool = Query(False),
    sort_by: str = "id", sort_order: str = "desc",
    db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user),
):
    result = await svc.list_sales_orders(
        db, page=page, page_size=page_size, customer_id=customer_id,
        status=status, sort_by=sort_by, sort_order=sort_order,
    )
    if include_ai and result["list"]:
        from app.services.sales_ai_service import enrich_order_list
        ai_map = await enrich_order_list(db, result["list"])
        result["ai"] = ai_map
    return ok(result)


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
        result = {**order.__dict__, "ai": ai_data}
    return ok(result)


@router.post("/sales-orders", status_code=201)
async def create_sales_order(
    body: SalesOrderCreate,
    db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user),
):
    data = body.model_dump()
    items_data = data.pop("items", [])
    order = await svc.create_sales_order(db, data, items_data)
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
    return ok({"deleted": len(body.ids)})


# ============================================================
# Delivery Note
# ============================================================

@router.get("/delivery-notes")
async def list_delivery_notes(
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    customer_id: int | None = None, status: str | None = None,
    sales_order_id: int | None = None,
    include_ai: bool = Query(False),
    sort_by: str = "id", sort_order: str = "desc",
    db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user),
):
    result = await svc.list_delivery_notes(
        db, page=page, page_size=page_size, customer_id=customer_id,
        status=status, sales_order_id=sales_order_id,
        sort_by=sort_by, sort_order=sort_order,
    )
    if include_ai and result["list"]:
        from app.services.sales_ai_service import enrich_delivery_list
        ai_map = await enrich_delivery_list(db, result["list"])
        result["ai"] = ai_map
    return ok(result)


@router.get("/delivery-notes/{note_id}")
async def get_delivery_note(
    note_id: int,
    include_ai: bool = Query(False),
    db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user),
):
    note = await svc.get_delivery_note(db, note_id)
    if not note:
        return fail("发货单不存在", 404)
    result = note
    if include_ai:
        from app.services.sales_ai_service import enrich_delivery_note
        ai_data = await enrich_delivery_note(db, note)
        result = {**note.__dict__, "ai": ai_data}
    return ok(result)


@router.post("/delivery-notes", status_code=201)
async def create_delivery_note(
    body: DeliveryNoteCreate,
    db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user),
):
    data = body.model_dump()
    items_data = data.pop("items", [])
    note = await svc.create_delivery_note(db, data, items_data)
    return ok(note)


@router.put("/delivery-notes/{note_id}")
async def update_delivery_note(
    note_id: int, body: DeliveryNoteUpdate,
    db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user),
):
    note = await svc.get_delivery_note(db, note_id)
    if not note:
        return fail("发货单不存在", 404)
    note = await svc.update_delivery_note(db, note, body.model_dump(exclude_none=True))
    return ok(note)


@router.delete("/delivery-notes/{note_id}")
async def delete_delivery_note(
    note_id: int,
    db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user),
):
    note = await svc.get_delivery_note(db, note_id)
    if not note:
        return fail("发货单不存在", 404)
    await svc.delete_delivery_note(db, note)
    return ok({"deleted": note_id})


@router.post("/delivery-notes/batch-delete")
async def batch_delete_delivery_notes(
    body: BatchDeleteRequest,
    db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user),
):
    for nid in body.ids:
        note = await svc.get_delivery_note(db, nid)
        if note:
            await svc.delete_delivery_note(db, note)
    return ok({"deleted": len(body.ids)})


# ============================================================
# Flow Conversions
# ============================================================

@router.post("/quotations/{quote_id}/convert-to-order")
async def convert_quote_to_order(
    quote_id: int,
    db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user),
):
    quote = await svc.get_quotation(db, quote_id)
    if not quote:
        return fail("报价单不存在", 404)
    if quote.status == "won":
        return fail("报价单已转换", 400)
    order = await svc.convert_quotation_to_order(db, quote)
    from app.services.sales_ai_pipeline import validate_quote_to_order
    validation = None
    try:
        ai_result = await validate_quote_to_order(db, quote)
        if ai_result:
            validation = ConversionValidation(**ai_result)
    except Exception:
        pass
    return ok(ConvertResponse(
        id=order.id,
        document_no=order.order_no or "",
        msg="报价单已转换为销售订单",
        ai_validation=validation,
    ))


@router.post("/sales-orders/{order_id}/convert-to-delivery")
async def convert_order_to_delivery(
    order_id: int,
    db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user),
):
    order = await svc.get_sales_order(db, order_id)
    if not order:
        return fail("销售订单不存在", 404)
    note = await svc.convert_order_to_delivery(db, order)
    if not note:
        return fail("订单已转换", 409)
    from app.services.sales_ai_pipeline import validate_order_to_delivery
    validation = None
    try:
        ai_result = await validate_order_to_delivery(db, order)
        if ai_result:
            validation = ConversionValidation(**ai_result)
    except Exception:
        pass
    return ok(ConvertResponse(
        id=note.id,
        document_no=note.delivery_no or "",
        msg="销售订单已转换为发货单",
        ai_validation=validation,
    ))
