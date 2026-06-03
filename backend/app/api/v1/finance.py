"""Finance API — invoices, payments, contracts, targets."""

import hashlib
import io
import json
import logging

from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.schemas.common import fail, ok
from app.schemas.finance import (
    ContractCreate, ContractUpdate,
    InvoiceCreate, InvoiceUpdate,
    PaymentRecordCreate, PaymentRecordUpdate,
    SalesTargetCreate, SalesTargetUpdate,
)
from app.services.cache_service import cache_bump_version, cache_get_versioned, cache_set_versioned

router = APIRouter(tags=["finance"])
logger = logging.getLogger(__name__)

# ============================================================
# Cache configuration
# ============================================================
# List endpoints: 5 min TTL, paginated/filterable
INVOICES_LIST_CACHE_TTL = 300
INVOICES_LIST_CACHE_VERSION = "v1"

PAYMENTS_LIST_CACHE_TTL = 300
PAYMENTS_LIST_CACHE_VERSION = "v1"

CONTRACTS_LIST_CACHE_TTL = 300
CONTRACTS_LIST_CACHE_VERSION = "v1"

TARGETS_LIST_CACHE_TTL = 300
TARGETS_LIST_CACHE_VERSION = "v1"

# Stats endpoints: shorter TTL for fresher aggregates
PAYMENTS_STATS_CACHE_TTL = 60
PAYMENTS_STATS_CACHE_VERSION = "v1"

TARGETS_STATS_CACHE_TTL = 120
TARGETS_STATS_CACHE_VERSION = "v1"


def _invoices_cache_key(**parts: object) -> str:
    canonical = json.dumps(parts, sort_keys=True, default=str)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]
    return f"invoices:list:{INVOICES_LIST_CACHE_VERSION}:{digest}"


def _payments_cache_key(**parts: object) -> str:
    canonical = json.dumps(parts, sort_keys=True, default=str)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]
    return f"payments:list:{PAYMENTS_LIST_CACHE_VERSION}:{digest}"


def _contracts_cache_key(**parts: object) -> str:
    canonical = json.dumps(parts, sort_keys=True, default=str)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]
    return f"contracts:list:{CONTRACTS_LIST_CACHE_VERSION}:{digest}"


def _targets_cache_key(**parts: object) -> str:
    canonical = json.dumps(parts, sort_keys=True, default=str)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]
    return f"targets:list:{TARGETS_LIST_CACHE_VERSION}:{digest}"


async def _bump_finance_invoice_caches() -> None:
    """Bump all caches that depend on invoice data."""
    await cache_bump_version("invoices:list")
    await cache_bump_version("finance:reports:pnl")
    await cache_bump_version("reports:predefined:ar")
    await cache_bump_version("dashboard:overview")
    await cache_bump_version("dashboard:kpi")


async def _bump_finance_payment_caches() -> None:
    """Bump all caches that depend on payment data."""
    await cache_bump_version("payments:list")
    await cache_bump_version("payments:stats")
    await cache_bump_version("reports:predefined:ar")
    await cache_bump_version("dashboard:overview")
    await cache_bump_version("dashboard:kpi")


# ============================================================
# Invoices
# ============================================================

@router.get("/invoices")
async def list_invoices(
    response: JSONResponse,
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    customer_id: int | None = None, status: str | None = None,
    sales_order_id: int | None = None,
    sort_by: str = "id", sort_order: str = "desc",
    db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user),
):
    cache_key = _invoices_cache_key(
        page=page, page_size=page_size, customer_id=customer_id,
        status=status, sales_order_id=sales_order_id,
        sort_by=sort_by, sort_order=sort_order,
    )
    cached_payload = await cache_get_versioned("invoices:list", cache_key)
    if cached_payload is not None:
        response.headers["X-Cache"] = "HIT"
        response.headers["X-Cache-Key"] = cache_key
        return ok(json.loads(cached_payload))
    response.headers["X-Cache"] = "MISS"
    from app.services.finance_service import list_invoices as svc_list
    result = await svc_list(db, page=page, page_size=page_size, customer_id=customer_id,
                          status=status, sales_order_id=sales_order_id,
                          sort_by=sort_by, sort_order=sort_order)
    await cache_set_versioned("invoices:list", cache_key, json.dumps(result, default=str),
                                INVOICES_LIST_CACHE_TTL)
    return ok(result)


@router.get("/invoices/{inv_id}")
async def get_invoice(inv_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    from app.services.finance_service import get_invoice as svc_get
    inv = await svc_get(db, inv_id)
    if not inv:
        return fail("发票不存在", 404)
    return ok(inv)


@router.post("/invoices")
async def create_invoice(body: InvoiceCreate, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    from app.services.finance_service import create_invoice as svc_create
    inv = await svc_create(db, body.model_dump())
    await _bump_finance_invoice_caches()
    return ok(inv)


@router.put("/invoices/{inv_id}")
async def update_invoice(inv_id: int, body: InvoiceUpdate, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    from app.services.finance_service import get_invoice as svc_get, update_invoice as svc_update
    inv = await svc_get(db, inv_id)
    if not inv:
        return fail("发票不存在", 404)
    inv = await svc_update(db, inv, body.model_dump(exclude_none=True))
    await _bump_finance_invoice_caches()
    return ok(inv)


@router.delete("/invoices/{inv_id}")
async def delete_invoice(inv_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    from app.services.finance_service import get_invoice as svc_get, delete_invoice as svc_del
    inv = await svc_get(db, inv_id)
    if not inv:
        return fail("发票不存在", 404)
    await svc_del(db, inv)
    await _bump_finance_invoice_caches()
    return ok({"deleted": inv_id})


# ============================================================
# Payments
# ============================================================

@router.get("/payments")
async def list_payments(
    response: JSONResponse,
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    customer_id: int | None = None, status: str | None = None,
    sales_order_id: int | None = None, delivery_note_id: int | None = None,
    sort_by: str = "id", sort_order: str = "desc",
    db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user),
):
    cache_key = _payments_cache_key(
        page=page, page_size=page_size, customer_id=customer_id,
        status=status, sales_order_id=sales_order_id,
        delivery_note_id=delivery_note_id, sort_by=sort_by, sort_order=sort_order,
    )
    cached_payload = await cache_get_versioned("payments:list", cache_key)
    if cached_payload is not None:
        response.headers["X-Cache"] = "HIT"
        response.headers["X-Cache-Key"] = cache_key
        return ok(json.loads(cached_payload))
    response.headers["X-Cache"] = "MISS"
    from app.services.finance_service import list_payments as svc_list
    result = await svc_list(db, page=page, page_size=page_size, customer_id=customer_id,
                          status=status, sales_order_id=sales_order_id,
                          delivery_note_id=delivery_note_id,
                          sort_by=sort_by, sort_order=sort_order)
    await cache_set_versioned("payments:list", cache_key, json.dumps(result, default=str),
                                PAYMENTS_LIST_CACHE_TTL)
    return ok(result)


@router.get("/payments/stats")
async def get_payment_stats(
    response: JSONResponse,
    db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user),
):
    cache_key = "payments:stats:global"
    cached_payload = await cache_get_versioned("payments:stats", cache_key)
    if cached_payload is not None:
        response.headers["X-Cache"] = "HIT"
        response.headers["X-Cache-Key"] = cache_key
        return ok(json.loads(cached_payload))
    response.headers["X-Cache"] = "MISS"
    from app.services.finance_service import payment_stats
    result = await payment_stats(db)
    await cache_set_versioned("payments:stats", cache_key, json.dumps(result, default=str),
                                PAYMENTS_STATS_CACHE_TTL)
    return ok(result)


@router.get("/payments/{pay_id}")
async def get_payment(pay_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    from app.services.finance_service import get_payment as svc_get
    pay = await svc_get(db, pay_id)
    if not pay:
        return fail("回款记录不存在", 404)
    return ok(pay)


@router.post("/payments")
async def create_payment(body: PaymentRecordCreate, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    from app.services.finance_service import create_payment as svc_create
    pay = await svc_create(db, body.model_dump())
    await _bump_finance_payment_caches()
    return ok(pay)


@router.put("/payments/{pay_id}")
async def update_payment(pay_id: int, body: PaymentRecordUpdate, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    from app.services.finance_service import get_payment as svc_get, update_payment as svc_update
    pay = await svc_get(db, pay_id)
    if not pay:
        return fail("回款记录不存在", 404)
    pay = await svc_update(db, pay, body.model_dump(exclude_none=True))
    await _bump_finance_payment_caches()
    return ok(pay)


@router.delete("/payments/{pay_id}")
async def delete_payment(pay_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    from app.services.finance_service import get_payment as svc_get, delete_payment as svc_del
    pay = await svc_get(db, pay_id)
    if not pay:
        return fail("回款记录不存在", 404)
    await svc_del(db, pay)
    await _bump_finance_payment_caches()
    return ok({"deleted": pay_id})


# ============================================================
# Contracts
# ============================================================

@router.get("/contracts")
async def list_contracts(
    response: JSONResponse,
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    customer_id: int | None = None, status: str | None = None,
    sort_by: str = "id", sort_order: str = "desc",
    db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user),
):
    cache_key = _contracts_cache_key(
        page=page, page_size=page_size, customer_id=customer_id,
        status=status, sort_by=sort_by, sort_order=sort_order,
    )
    cached_payload = await cache_get_versioned("contracts:list", cache_key)
    if cached_payload is not None:
        response.headers["X-Cache"] = "HIT"
        response.headers["X-Cache-Key"] = cache_key
        return ok(json.loads(cached_payload))
    response.headers["X-Cache"] = "MISS"
    from app.services.finance_service import list_contracts as svc_list
    result = await svc_list(db, page=page, page_size=page_size, customer_id=customer_id,
                          status=status, sort_by=sort_by, sort_order=sort_order)
    await cache_set_versioned("contracts:list", cache_key, json.dumps(result, default=str),
                                CONTRACTS_LIST_CACHE_TTL)
    return ok(result)


@router.get("/contracts/{contract_id}")
async def get_contract(contract_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    from app.services.finance_service import get_contract as svc_get
    ct = await svc_get(db, contract_id)
    if not ct:
        return fail("合同不存在", 404)
    return ok(ct)


@router.post("/contracts")
async def create_contract(body: ContractCreate, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    from app.services.finance_service import create_contract as svc_create
    ct = await svc_create(db, body.model_dump())
    await cache_bump_version("contracts:list")
    return ok(ct)


@router.put("/contracts/{contract_id}")
async def update_contract(contract_id: int, body: ContractUpdate, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    from app.services.finance_service import get_contract as svc_get, update_contract as svc_update
    ct = await svc_get(db, contract_id)
    if not ct:
        return fail("合同不存在", 404)
    ct = await svc_update(db, ct, body.model_dump(exclude_none=True))
    await cache_bump_version("contracts:list")
    return ok(ct)


@router.delete("/contracts/{contract_id}")
async def delete_contract(contract_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    from app.services.finance_service import get_contract as svc_get, delete_contract as svc_del
    ct = await svc_get(db, contract_id)
    if not ct:
        return fail("合同不存在", 404)
    await svc_del(db, ct)
    await cache_bump_version("contracts:list")
    return ok({"deleted": contract_id})


# ---------------------------------------------------------------------------
# Contract PDF Import with AI OCR
# ---------------------------------------------------------------------------
CONTRACT_PARSE_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string", "description": "合同标题/名称"},
        "contract_no": {"type": "string", "description": "合同编号"},
        "amount": {"type": "number", "description": "合同金额(元)"},
        "signed_date": {"type": "string", "description": "签署日期 YYYY-MM-DD"},
        "expire_date": {"type": "string", "description": "到期日期 YYYY-MM-DD"},
        "buyer_name": {"type": "string", "description": "买方/客户公司名称"},
        "seller_name": {"type": "string", "description": "卖方/供应商公司名称"},
        "notes": {"type": "string", "description": "合同主要条款摘要(50字内)"},
    },
    "required": ["title"],
}


def _extract_pdf_text(content: bytes) -> str:
    """Extract text from PDF bytes. Returns empty string on failure."""
    try:
        from PyPDF2 import PdfReader
        reader = PdfReader(io.BytesIO(content))
        texts = []
        for page in reader.pages:
            t = page.extract_text()
            if t:
                texts.append(t)
        return "\n".join(texts).strip()
    except Exception as e:
        logger.warning(f"PyPDF2 extraction failed: {e}")
        return ""


def _ocr_pdf_content(content: bytes) -> str:
    """Attempt OCR on a PDF by treating raw bytes as image. Fallback only."""
    try:
        from PIL import Image
        import pytesseract
        img = Image.open(io.BytesIO(content))
        return pytesseract.image_to_string(img, lang="chi_sim+eng")
    except Exception:
        return ""


@router.post("/contracts/import-pdf")
async def import_contract_pdf(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Upload a PDF contract, extract text via OCR/AI, parse into contract fields."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        return fail("请上传PDF文件")

    content = await file.read()
    if len(content) > 20 * 1024 * 1024:
        return fail("文件大小不能超过 20MB")

    # Step 1: Extract text
    raw_text = _extract_pdf_text(content)

    # Step 2: If text is too short, try OCR on first page
    if len(raw_text) < 50:
        ocr_text = _ocr_pdf_content(content)
        if ocr_text:
            raw_text = ocr_text

    if not raw_text or len(raw_text) < 10:
        return fail("无法从 PDF 中提取文字，请确认文件是否为扫描件或图片格式 PDF")

    # Step 3: AI parsing
    from app.services.ai.client import AIClient
    ai = AIClient()
    try:
        parsed = await ai.chat_structured(
            messages=[
                {"role": "system", "content": "你是一个合同解析助手。从合同文本中提取关键信息，返回JSON。金额单位是元。日期格式YYYY-MM-DD。提取不到就省略字段，不要编造数据。"},
                {"role": "user", "content": f"请从以下合同文本中提取关键信息:\n\n{raw_text[:4000]}"},
            ],
            output_schema=CONTRACT_PARSE_SCHEMA,
            temperature=0.1,
        )
    except Exception as e:
        logger.exception("AI parsing failed")
        return fail(f"AI解析失败: {str(e)}")

    # Step 4: Try to find customer by name
    customer_id = None
    buyer_name = parsed.get("buyer_name", "")
    if buyer_name:
        from sqlalchemy import select
        from app.models.customer import Customer
        result = await db.execute(
            select(Customer.id).where(Customer.name.ilike(f"%{buyer_name}%"))
        )
        cid = result.scalar_one_or_none()
        if cid:
            customer_id = cid

    if not customer_id:
        return fail(f"未找到匹配客户: {buyer_name or '(未能识别买方名称)'}，请先在客户管理中创建客户")

    # Step 5: Create contract
    from app.services.finance_service import create_contract as svc_create
    ct_data = {
        "title": parsed.get("title", file.filename or "未命名合同"),
        "contract_no": parsed.get("contract_no", ""),
        "customer_id": customer_id,
        "amount": float(parsed.get("amount", 0)),
        "signed_date": parsed.get("signed_date", ""),
        "expire_date": parsed.get("expire_date", ""),
        "notes": parsed.get("notes", ""),
        "status": "signed",
    }
    ct = await svc_create(db, ct_data)
    await cache_bump_version("contracts:list")

    return ok({
        "id": ct.id,
        "parsed": {
            "title": parsed.get("title"),
            "amount": parsed.get("amount"),
            "signed_date": parsed.get("signed_date"),
            "buyer_name": buyer_name,
        },
    })


@router.get("/targets")
async def list_targets(
    response: JSONResponse,
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    user_id: int | None = None, status: str | None = None,
    target_type: str | None = None,
    sort_by: str = "id", sort_order: str = "desc",
    db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user),
):
    cache_key = _targets_cache_key(
        page=page, page_size=page_size, user_id=user_id,
        status=status, target_type=target_type,
        sort_by=sort_by, sort_order=sort_order,
    )
    cached_payload = await cache_get_versioned("targets:list", cache_key)
    if cached_payload is not None:
        response.headers["X-Cache"] = "HIT"
        response.headers["X-Cache-Key"] = cache_key
        return ok(json.loads(cached_payload))
    response.headers["X-Cache"] = "MISS"
    from app.services.finance_service import list_targets as svc_list
    result = await svc_list(db, page=page, page_size=page_size, user_id=user_id,
                          status=status, target_type=target_type,
                          sort_by=sort_by, sort_order=sort_order)
    await cache_set_versioned("targets:list", cache_key, json.dumps(result, default=str),
                                TARGETS_LIST_CACHE_TTL)
    return ok(result)


@router.get("/targets/stats")
async def get_target_stats(
    response: JSONResponse,
    db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user),
):
    cache_key = "targets:stats:global"
    cached_payload = await cache_get_versioned("targets:stats", cache_key)
    if cached_payload is not None:
        response.headers["X-Cache"] = "HIT"
        response.headers["X-Cache-Key"] = cache_key
        return ok(json.loads(cached_payload))
    response.headers["X-Cache"] = "MISS"
    from app.services.finance_service import target_stats
    result = await target_stats(db)
    await cache_set_versioned("targets:stats", cache_key, json.dumps(result, default=str),
                                TARGETS_STATS_CACHE_TTL)
    return ok(result)


@router.get("/targets/{target_id}")
async def get_target(target_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    from app.services.finance_service import get_target as svc_get
    t = await svc_get(db, target_id)
    if not t:
        return fail("目标不存在", 404)
    return ok(t)


@router.post("/targets")
async def create_target(body: SalesTargetCreate, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    from app.services.finance_service import create_target as svc_create
    t = await svc_create(db, body.model_dump())
    await cache_bump_version("targets:list")
    await cache_bump_version("targets:stats")
    return ok(t)


@router.put("/targets/{target_id}")
async def update_target(target_id: int, body: SalesTargetUpdate, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    from app.services.finance_service import get_target as svc_get, update_target as svc_update
    t = await svc_get(db, target_id)
    if not t:
        return fail("目标不存在", 404)
    t = await svc_update(db, t, body.model_dump(exclude_none=True))
    await cache_bump_version("targets:list")
    await cache_bump_version("targets:stats")
    return ok(t)


@router.delete("/targets/{target_id}")
async def delete_target(target_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    from app.services.finance_service import get_target as svc_get, delete_target as svc_del
    t = await svc_get(db, target_id)
    if not t:
        return fail("目标不存在", 404)
    await svc_del(db, t)
    await cache_bump_version("targets:list")
    await cache_bump_version("targets:stats")
    return ok({"deleted": target_id})
