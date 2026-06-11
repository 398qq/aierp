"""Contract intelligence routes."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.schemas.common import fail, ok

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/contracts/{contract_id}/extract")
async def contract_extract(
    contract_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Extract key terms and clauses from a contract."""
    from app.services.contract_intel_service import extract_contract_terms

    try:
        result = await extract_contract_terms(db, contract_id)
        return ok(result)
    except ValueError as e:
        return fail(str(e), 404)


@router.post("/contracts/{contract_id}/risk")
async def contract_risk(
    contract_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Assess risk factors in a contract (price lock, exclusivity, penalty clauses)."""
    from app.services.contract_intel_service import assess_contract_risk

    try:
        result = await assess_contract_risk(db, contract_id)
        return ok(result)
    except ValueError as e:
        return fail(str(e), 404)


@router.post("/contracts/expiry-alerts")
async def contract_expiry_alerts(
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Scan contracts expiring in the next 90 days."""
    from app.services.contract_intel_service import scan_contract_expiry

    try:
        result = await scan_contract_expiry(db)
        return ok(result)
    except ValueError as e:
        return fail(str(e), 404)


@router.post("/contracts/{contract_id}/rebate-tracking")
async def contract_rebate(
    contract_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Track rebate fulfillment status for a contract."""
    from app.services.contract_intel_service import track_contract_rebate

    try:
        result = await track_contract_rebate(db, contract_id)
        return ok(result)
    except ValueError as e:
        return fail(str(e), 404)
