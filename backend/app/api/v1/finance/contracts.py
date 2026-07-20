"""Finance API — contract bounded context.

Routes for the contract lifecycle:
- list / get / create / update / delete
- PDF import (AI OCR + structured extraction)

The PDF import endpoint is heavy: it reads the file, extracts text via
PyPDF2 with Tesseract fallback, then runs an LLM call to parse
structured fields. It is NOT cached (per-call cost is dominated by
the LLM, not the DB).
"""

import asyncio
import io
import json
import logging

from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy import inspect as sa_inspect
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.permissions import write_audit_log
from app.api.v1.finance._shared import (
    CONTRACTS_LIST_CACHE_TTL,
    _contracts_cache_key,
)
from app.database import get_db
from app.models.customer import Customer
from app.schemas.common import APIResponse, PageData, fail, ok
from app.schemas.finance import ContractCreate, ContractResponse, ContractUpdate
from app.services.cache_service import (
    cache_bump_version,
    cache_get_versioned,
    cache_set_versioned,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["finance:contract"])
CONTRACT_PDF_AI_TIMEOUT_SECONDS = 45


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


def _serialize_contract(ct) -> dict:
    """Convert a Contract ORM object to a JSON-safe dict."""
    state = sa_inspect(ct)
    customer = ct.customer if "customer" not in state.unloaded else None
    return {
        "id": ct.id,
        "contract_no": ct.contract_no,
        "customer_id": ct.customer_id,
        "customer_name": customer.name if customer else None,
        "sales_order_id": ct.sales_order_id,
        "title": ct.title,
        "amount": float(ct.amount) if ct.amount else 0.0,
        "currency": ct.currency,
        "signed_date": ct.signed_date.isoformat() if ct.signed_date else None,
        "expire_date": ct.expire_date.isoformat() if ct.expire_date else None,
        "status": ct.status,
        "file_url": ct.file_url,
        "delivery_address": ct.delivery_address,
        "delivery_terms": ct.delivery_terms,
        "payment_terms": ct.payment_terms,
        "acceptance_terms": ct.acceptance_terms,
        "warranty_terms": ct.warranty_terms,
        "dispute_terms": ct.dispute_terms,
        "invoice_type": ct.invoice_type,
        "notes": ct.notes,
        "created_at": ct.created_at.isoformat() if ct.created_at else None,
        "updated_at": ct.updated_at.isoformat() if ct.updated_at else None,
    }


@router.get("/contracts", response_model=APIResponse[PageData[ContractResponse]])
async def list_contracts(
    response: JSONResponse,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    customer_id: int | None = None,
    status: str | None = None,
    sort_by: str = "id",
    sort_order: str = "desc",
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    cache_key = _contracts_cache_key(
        page=page,
        page_size=page_size,
        customer_id=customer_id,
        status=status,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    cached_payload = await cache_get_versioned("contracts:list", cache_key)
    if cached_payload is not None:
        parsed = json.loads(cached_payload)
        items = parsed.get("list") if isinstance(parsed, dict) else None
        # Guard against stale pre-serialization cache (ORM objects → strings)
        if items is None or (items and not isinstance(items[0], dict)):
            pass  # stale — fall through to MISS and overwrite
        else:
            response.headers["X-Cache"] = "HIT"
            response.headers["X-Cache-Key"] = cache_key
            return ok(parsed)
    response.headers["X-Cache"] = "MISS"
    from app.services.finance_service import list_contracts as svc_list

    result = await svc_list(
        db,
        page=page,
        page_size=page_size,
        customer_id=customer_id,
        status=status,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    # Eager-load customers to avoid N+1 during serialization
    contracts = list(result["list"])
    if contracts:
        cust_ids = list({c.customer_id for c in contracts if c.customer_id})
        if cust_ids:
            cust_map = {
                c.id: c
                for c in (
                    await db.execute(select(Customer).where(Customer.id.in_(cust_ids)))
                )
                .scalars()
                .all()
            }
            for ct in contracts:
                ct.customer = cust_map.get(ct.customer_id)
    serialized = {**result, "list": [_serialize_contract(c) for c in contracts]}
    await cache_set_versioned(
        "contracts:list",
        cache_key,
        json.dumps(serialized),
        CONTRACTS_LIST_CACHE_TTL,
    )
    return ok(serialized)


@router.post("/contracts", response_model=APIResponse[ContractResponse])
async def create_contract(
    body: ContractCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    from app.services.finance_service import create_contract as svc_create

    ct = await svc_create(db, body.model_dump())
    await cache_bump_version("contracts:list")
    await write_audit_log(
        db,
        current_user["user_id"],
        current_user["username"],
        "create",
        "contract",
        ct.id,
        f"创建合同 {ct.contract_no or ct.id}",
    )
    return ok(_serialize_contract(ct))


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

    raw_text = _extract_pdf_text(content)

    if len(raw_text) < 50:
        ocr_text = _ocr_pdf_content(content)
        if ocr_text:
            raw_text = ocr_text

    if not raw_text or len(raw_text) < 10:
        return fail("无法从 PDF 中提取文字，请确认文件是否为扫描件或图片格式 PDF")

    from app.services.ai.client import AIClient

    ai = AIClient()
    try:
        parsed = await asyncio.wait_for(
            ai.chat_structured(
                messages=[
                    {
                        "role": "system",
                        "content": "你是一个合同解析助手。从合同文本中提取关键信息，返回JSON。金额单位是元。日期格式YYYY-MM-DD。提取不到就省略字段，不要编造数据。",
                    },
                    {
                        "role": "user",
                        "content": f"请从以下合同文本中提取关键信息:\n\n{raw_text[:4000]}",
                    },
                ],
                output_schema=CONTRACT_PARSE_SCHEMA,
                temperature=0.1,
            ),
            timeout=CONTRACT_PDF_AI_TIMEOUT_SECONDS,
        )
    except TimeoutError:
        return fail("AI解析超时，请稍后重试或改用手工录入")
    except Exception as e:
        logger.exception("AI parsing failed")
        return fail(f"AI解析失败: {str(e)}")

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
        return fail(
            f"未找到匹配客户: {buyer_name or '(未能识别买方名称)'}，请先在客户管理中创建客户"
        )

    from app.services.finance_service import create_contract as svc_create

    ct_data = {
        "title": parsed.get("title", file.filename or "未命名合同"),
        "contract_no": parsed.get("contract_no", ""),
        "customer_id": customer_id,
        "amount": float(parsed.get("amount", 0)),
        "signed_date": parsed.get("signed_date", ""),
        "expire_date": parsed.get("expire_date", ""),
        "notes": parsed.get("notes", ""),
        "status": "signed" if parsed.get("signed_date") else "draft",
    }
    ct = await svc_create(db, ct_data)
    await cache_bump_version("contracts:list")
    await write_audit_log(
        db,
        current_user["user_id"],
        current_user["username"],
        "import_pdf",
        "contract",
        ct.id,
        f"PDF导入合同 {ct.contract_no or ct.id}",
    )

    return ok(
        {
            "id": ct.id,
            "parsed": {
                "title": parsed.get("title"),
                "amount": parsed.get("amount"),
                "signed_date": parsed.get("signed_date"),
                "buyer_name": buyer_name,
            },
        }
    )


@router.get("/contracts/{contract_id}", response_model=APIResponse[ContractResponse])
async def get_contract(
    contract_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    from app.services.finance_service import get_contract as svc_get

    ct = await svc_get(db, contract_id)
    if not ct:
        return fail("合同不存在", 404)
    return ok(_serialize_contract(ct))


@router.put("/contracts/{contract_id}", response_model=APIResponse[ContractResponse])
async def update_contract(
    contract_id: int,
    body: ContractUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    from app.services.finance_service import (
        get_contract as svc_get,
        update_contract as svc_update,
    )

    ct = await svc_get(db, contract_id)
    if not ct:
        return fail("合同不存在", 404)
    previous_status = ct.status
    ct = await svc_update(
        db,
        ct,
        body.model_dump(exclude_none=True),
        actor=current_user["user_id"],
    )
    await cache_bump_version("contracts:list")
    await write_audit_log(
        db,
        current_user["user_id"],
        current_user["username"],
        "update",
        "contract",
        ct.id,
        f"更新合同 {ct.contract_no or ct.id}: {previous_status} -> {ct.status}",
    )
    return ok(_serialize_contract(ct))


@router.delete("/contracts/{contract_id}")
async def delete_contract(
    contract_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    from app.services.finance_service import (
        get_contract as svc_get,
        delete_contract as svc_del,
    )

    ct = await svc_get(db, contract_id)
    if not ct:
        return fail("合同不存在", 404)
    await svc_del(db, ct)
    await cache_bump_version("contracts:list")
    await write_audit_log(
        db,
        current_user["user_id"],
        current_user["username"],
        "delete",
        "contract",
        contract_id,
        f"删除草稿合同 {ct.contract_no or contract_id}",
    )
    return ok({"deleted": contract_id})
