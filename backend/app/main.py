from contextlib import asynccontextmanager
import time

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import httpx
from sqlalchemy import text
from starlette.responses import JSONResponse

from app.api.v1.router import api_router
from app.config import settings
from app.core.error_handlers import register_exception_handlers
from app.core.rate_limit import RateLimitMiddleware
from app.core.request_logging import RequestLoggingMiddleware
from app.core.request_context import RequestContextMiddleware
from app.core.security_headers import SecurityHeadersMiddleware
from app.database import engine, init_db
from app.services.cache_service import get_redis

# Import all models so Base.metadata knows about every table
import app.models.account  # noqa: F401
import app.models.approval  # noqa: F401
import app.models.customer  # noqa: F401
import app.models.finance  # noqa: F401
import app.models.product  # noqa: F401
import app.models.rbac  # noqa: F401
import app.models.report  # noqa: F401
import app.models.sales  # noqa: F401
import app.models.transaction  # noqa: F401
import app.models.user  # noqa: F401


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
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
