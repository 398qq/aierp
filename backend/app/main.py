from contextlib import asynccontextmanager
from importlib import import_module
import time

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import httpx
from sqlalchemy import text
from starlette.responses import JSONResponse, PlainTextResponse

from app.api.v1.router import api_router
from app.config import settings
from app.core.error_handlers import register_exception_handlers
from app.core.rate_limit import RateLimitMiddleware
from app.core.request_logging import RequestLoggingMiddleware
from app.core.request_context import RequestContextMiddleware
from app.core.security_headers import SecurityHeadersMiddleware
from app.database import engine, init_db
from app.services.cache_service import get_redis

# Import all models so Base.metadata knows about every table.
for _model_module in (
    "app.models.account",
    "app.models.approval",
    "app.models.customer",
    "app.models.finance",
    "app.models.product",
    "app.models.rbac",
    "app.models.report",
    "app.models.sales",
    "app.models.transaction",
    "app.models.user",
):
    import_module(_model_module)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    from app.application.event_handlers import (
        register_default_handlers,
        register_inventory_handlers,
    )
    from app.core.event_bus import event_bus
    from app.application.uow import init_uow
    from app.database import async_session
    register_default_handlers(event_bus)
    register_inventory_handlers(event_bus)
    init_uow(async_session)
    from app.jobs.scheduler import start, shutdown
    start()
    try:
        yield
    finally:
        shutdown()


app = FastAPI(title=settings.APP_NAME, version=settings.VERSION, lifespan=lifespan)
_started_at = time.time()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(RateLimitMiddleware)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestContextMiddleware)
register_exception_handlers(app)

app.include_router(api_router)


async def _check_database() -> str:
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return "ok"
    except Exception:
        return "error"


async def _check_redis() -> str:
    try:
        redis_conn = await get_redis()
        if redis_conn is None:
            return "unavailable"
        await redis_conn.ping()
        return "ok"
    except Exception:
        return "unavailable"


async def _check_ai_service() -> str:
    if not settings.AI_BASE_URL:
        return "unavailable"
    if not settings.AI_API_KEY:
        return "unavailable"

    url = settings.AI_BASE_URL.rstrip("/") + "/models"
    headers = {"Authorization": f"Bearer {settings.AI_API_KEY}"}

    try:
        async with httpx.AsyncClient(trust_env=False, timeout=4) as client:
            resp = await client.get(url, headers=headers)
        # 4xx still means remote endpoint is reachable.
        return "ok" if resp.status_code < 500 else "unavailable"
    except Exception:
        return "unavailable"


@app.get("/health")
async def health():
    db_status = await _check_database()
    redis_status = await _check_redis()
    ai_status = await _check_ai_service()

    if db_status != "ok":
        status = "down"
    elif redis_status == "ok" and ai_status == "ok":
        status = "ok"
    else:
        status = "degraded"

    return {
        "status": status,
        "checks": {
            "database": db_status,
            "redis": redis_status,
            "ai_service": ai_status,
        },
        "uptime_seconds": int(time.time() - _started_at),
        "version": settings.VERSION,
        "service": settings.APP_NAME,
    }


@app.get("/health/ready")
async def health_ready():
    db_status = await _check_database()
    if db_status != "ok":
        return JSONResponse(status_code=503, content={"status": "down", "checks": {"database": db_status}})
    return {"status": "ok", "checks": {"database": db_status}}


@app.get("/health/live")
async def health_live():
    return {"status": "ok"}


@app.get("/metrics")
async def metrics():
    """In-process metrics snapshot. Plug into Prometheus by replacing the
    primitives in `core.observability.metrics` with `prometheus_client` types."""
    from app.core.observability.metrics import all_snapshots
    return all_snapshots()


@app.get("/metrics/prometheus", response_class=PlainTextResponse)
async def metrics_prometheus():
    """Prometheus text exposition format — drop-in for scraping."""
    from app.core.observability.metrics import (
        cache_hit_ratio, cache_hits_total, cache_misses_total, render_prometheus_text,
    )
    # Sample cache_hit_ratio per family (Prometheus prefers gauges over computed values)
    for family in ("products:list", "customers:list", "sales-orders:list",
                   "opportunities:list", "quotations:list", "ai:enrich:opp_list",
                   "ai:enrich:quote_list", "ai:enrich:order_list",
                   "invoices:list", "payments:list", "payments:stats",
                   "contracts:list", "targets:list", "targets:stats",
                   "accounts:list", "journal-entries:list", "bank-reconciliations:list",
                   "finance:reports:pnl", "finance:reports:ap",
                   "reports:templates:list", "reports:predefined:sales",
                   "reports:predefined:ar", "reports:predefined:inventory",
                   "reports:predefined:procurement"):
        hits = cache_hits_total.value(family=family)
        misses = cache_misses_total.value(family=family)
        total = hits + misses
        if total > 0:
            cache_hit_ratio.set(hits / total, family=family)
    return PlainTextResponse(
        content=render_prometheus_text(),
        media_type="text/plain; version=0.0.4",
    )
