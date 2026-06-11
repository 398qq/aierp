"""Finance intelligence routes — payment prediction, cash flow, dunning, credit risk."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.schemas.common import fail, ok

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/finance/payment-prediction")
async def finance_payment_prediction(
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Predict which customers are likely to delay payments."""
    from app.services.finance_intel_service import predict_payment_delays

    try:
        result = await predict_payment_delays(db)
        return ok(result)
    except ValueError as e:
        return fail(str(e), 404)


@router.post("/finance/cash-flow")
async def finance_cash_flow(
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Forecast future cash flow based on AR/AP patterns."""
    from app.services.finance_intel_service import forecast_cash_flow

    try:
        result = await forecast_cash_flow(db)
        return ok(result)
    except ValueError as e:
        return fail(str(e), 404)


@router.post("/finance/dunning/{invoice_id}")
async def finance_dunning(
    invoice_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Generate a dunning strategy for an overdue invoice."""
    from app.services.finance_intel_service import generate_dunning_strategy

    try:
        result = await generate_dunning_strategy(db, invoice_id)
        return ok(result)
    except ValueError as e:
        return fail(str(e), 404)


@router.post("/finance/credit-risk/{customer_id}")
async def finance_credit_risk(
    customer_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Assess credit risk for a customer."""
    from app.services.finance_intel_service import assess_credit_risk

    try:
        result = await assess_credit_risk(db, customer_id)
        return ok(result)
    except ValueError as e:
        return fail(str(e), 404)
