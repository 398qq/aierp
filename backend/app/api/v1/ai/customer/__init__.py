"""Customer AI bounded-context package.

Composes the four customer AI sub-routers (recognition, insights,
work-queue, embedding) under a single ``/ai`` APIRouter so the
existing mount-point in ``app.api.v1.ai.__init__`` keeps working
without modification.

Each sub-router is independently importable so tests can target a
single bounded context (e.g. ``from app.api.v1.ai.customer.recognition
import _normalize_customer_recognition``).
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.ai.customer import embedding, insights, recognition, work_queue

# Composed router — exposes /ai/* endpoints identical to the previous
# monolithic ``customer_ai`` module.
router = APIRouter(prefix="/ai", tags=["ai"])
router.include_router(recognition.router)
router.include_router(insights.router)
router.include_router(work_queue.router)
router.include_router(embedding.router)

# Re-exports for back-compat with the original ``app.api.v1.ai.customer_ai``
# module path that the test suite monkeypatches through.
recognition_router = recognition.router
insights_router = insights.router
work_queue_router = work_queue.router
embedding_router = embedding.router

__all__ = [
    "router",
    "recognition_router",
    "insights_router",
    "work_queue_router",
    "embedding_router",
    "recognition",
    "insights",
    "work_queue",
    "embedding",
]
