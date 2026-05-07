from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.config import settings
from app.database import init_db
from app.jobs.scheduler import start_scheduler, stop_scheduler

# Import all models so Base.metadata knows about every table
import app.models.customer  # noqa: F401
import app.models.finance  # noqa: F401
import app.models.product  # noqa: F401
import app.models.sales  # noqa: F401
import app.models.transaction  # noqa: F401
import app.models.user  # noqa: F401


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    if settings.AI_API_KEY:
        start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(title=settings.APP_NAME, version=settings.VERSION, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": settings.APP_NAME}
