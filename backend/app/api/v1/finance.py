"""Finance API — invoices, payments, contracts, targets."""

from fastapi import APIRouter, Depends, Query
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

router = APIRouter(tags=["finance"])

# ============================================================
# Invoices
# ============================================================

@router.get("/invoices")
async def list_invoices(
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    customer_id: int | None = None, status: str | None = None,
    sales_order_id: int | None = None,
    sort_by: str = "id", sort_order: str = "desc",
    db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user),
):
    from app.services.finance_service import list_invoices as svc_list
    result = await svc_list(db, page=page, page_size=page_size, customer_id=customer_id,
                          status=status, sales_order_id=sales_order_id,
                          sort_by=sort_by, sort_order=sort_order)
    return ok(result)


@router.get("/invoices/{inv_id}")
async def get_invoice(inv_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    from app.services.finance_service import get_invoice as svc_get
    inv = await svc_get(db, inv_id)
    if not inv: return fail("发票不存在", 404)
    return ok(inv)


@router.post("/invoices")
async def create_invoice(body: InvoiceCreate, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    from app.services.finance_service import create_invoice as svc_create
    inv = await svc_create(db, body.model_dump())
    return ok(inv, code=201)


@router.put("/invoices/{inv_id}")
async def update_invoice(inv_id: int, body: InvoiceUpdate, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    from app.services.finance_service import get_invoice as svc_get, update_invoice as svc_update
    inv = await svc_get(db, inv_id)
    if not inv: return fail("发票不存在", 404)
    inv = await svc_update(db, inv, body.model_dump(exclude_none=True))
    return ok(inv)


@router.delete("/invoices/{inv_id}")
async def delete_invoice(inv_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    from app.services.finance_service import get_invoice as svc_get, delete_invoice as svc_del
    inv = await svc_get(db, inv_id)
    if not inv: return fail("发票不存在", 404)
    await svc_del(db, inv)
    return ok({"deleted": inv_id})


# ============================================================
# Payments
# ============================================================

@router.get("/payments")
async def list_payments(
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    customer_id: int | None = None, status: str | None = None,
    sales_order_id: int | None = None,
    sort_by: str = "id", sort_order: str = "desc",
    db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user),
):
    from app.services.finance_service import list_payments as svc_list
    result = await svc_list(db, page=page, page_size=page_size, customer_id=customer_id,
                          status=status, sales_order_id=sales_order_id,
                          sort_by=sort_by, sort_order=sort_order)
    return ok(result)


@router.get("/payments/stats")
async def get_payment_stats(db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    from app.services.finance_service import payment_stats
    return ok(await payment_stats(db))


@router.get("/payments/{pay_id}")
async def get_payment(pay_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    from app.services.finance_service import get_payment as svc_get
    pay = await svc_get(db, pay_id)
    if not pay: return fail("回款记录不存在", 404)
    return ok(pay)


@router.post("/payments")
async def create_payment(body: PaymentRecordCreate, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    from app.services.finance_service import create_payment as svc_create
    pay = await svc_create(db, body.model_dump())
    return ok(pay, code=201)


@router.put("/payments/{pay_id}")
async def update_payment(pay_id: int, body: PaymentRecordUpdate, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    from app.services.finance_service import get_payment as svc_get, update_payment as svc_update
    pay = await svc_get(db, pay_id)
    if not pay: return fail("回款记录不存在", 404)
    pay = await svc_update(db, pay, body.model_dump(exclude_none=True))
    return ok(pay)


@router.delete("/payments/{pay_id}")
async def delete_payment(pay_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    from app.services.finance_service import get_payment as svc_get, delete_payment as svc_del
    pay = await svc_get(db, pay_id)
    if not pay: return fail("回款记录不存在", 404)
    await svc_del(db, pay)
    return ok({"deleted": pay_id})


# ============================================================
# Contracts
# ============================================================

@router.get("/contracts")
async def list_contracts(
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    customer_id: int | None = None, status: str | None = None,
    sort_by: str = "id", sort_order: str = "desc",
    db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user),
):
    from app.services.finance_service import list_contracts as svc_list
    result = await svc_list(db, page=page, page_size=page_size, customer_id=customer_id,
                          status=status, sort_by=sort_by, sort_order=sort_order)
    return ok(result)


@router.get("/contracts/{contract_id}")
async def get_contract(contract_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    from app.services.finance_service import get_contract as svc_get
    ct = await svc_get(db, contract_id)
    if not ct: return fail("合同不存在", 404)
    return ok(ct)


@router.post("/contracts")
async def create_contract(body: ContractCreate, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    from app.services.finance_service import create_contract as svc_create
    ct = await svc_create(db, body.model_dump())
    return ok(ct, code=201)


@router.put("/contracts/{contract_id}")
async def update_contract(contract_id: int, body: ContractUpdate, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    from app.services.finance_service import get_contract as svc_get, update_contract as svc_update
    ct = await svc_get(db, contract_id)
    if not ct: return fail("合同不存在", 404)
    ct = await svc_update(db, ct, body.model_dump(exclude_none=True))
    return ok(ct)


@router.delete("/contracts/{contract_id}")
async def delete_contract(contract_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    from app.services.finance_service import get_contract as svc_get, delete_contract as svc_del
    ct = await svc_get(db, contract_id)
    if not ct: return fail("合同不存在", 404)
    await svc_del(db, ct)
    return ok({"deleted": contract_id})


# ============================================================
# Sales Targets
# ============================================================

@router.get("/targets")
async def list_targets(
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    user_id: int | None = None, status: str | None = None,
    target_type: str | None = None,
    sort_by: str = "id", sort_order: str = "desc",
    db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user),
):
    from app.services.finance_service import list_targets as svc_list
    result = await svc_list(db, page=page, page_size=page_size, user_id=user_id,
                          status=status, target_type=target_type,
                          sort_by=sort_by, sort_order=sort_order)
    return ok(result)


@router.get("/targets/stats")
async def get_target_stats(db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    from app.services.finance_service import target_stats
    return ok(await target_stats(db))


@router.get("/targets/{target_id}")
async def get_target(target_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    from app.services.finance_service import get_target as svc_get
    t = await svc_get(db, target_id)
    if not t: return fail("目标不存在", 404)
    return ok(t)


@router.post("/targets")
async def create_target(body: SalesTargetCreate, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    from app.services.finance_service import create_target as svc_create
    t = await svc_create(db, body.model_dump())
    return ok(t, code=201)


@router.put("/targets/{target_id}")
async def update_target(target_id: int, body: SalesTargetUpdate, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    from app.services.finance_service import get_target as svc_get, update_target as svc_update
    t = await svc_get(db, target_id)
    if not t: return fail("目标不存在", 404)
    t = await svc_update(db, t, body.model_dump(exclude_none=True))
    return ok(t)


@router.delete("/targets/{target_id}")
async def delete_target(target_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    from app.services.finance_service import get_target as svc_get, delete_target as svc_del
    t = await svc_get(db, target_id)
    if not t: return fail("目标不存在", 404)
    await svc_del(db, t)
    return ok({"deleted": target_id})
