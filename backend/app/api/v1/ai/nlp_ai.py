"""Natural language ERP query routes."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.schemas.common import fail, ok

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/query")
async def ai_query(
    data: dict,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Answer natural language questions about ERP data."""
    from app.services.nlp_query_service import natural_language_query

    query_text = data.get("query", "")
    if not query_text:
        return fail("query is required", 400)
    try:
        result = await natural_language_query(db, query_text)
        return ok(result)
    except ValueError as e:
        return fail(str(e), 404)