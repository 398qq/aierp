"""Customer AI — embedding endpoints.

Generate and query customer embedding vectors stored in pgvector:

* ``POST /customer/{id}/embed``      — embed a single customer
* ``GET  /customer/{id}/similar``    — top-k neighbours
* ``GET  /customer/similar/search``  — text → top-k neighbours
* ``POST /customer/embed-all``       — batch-embed missing customers
* ``GET  /customer/segments``        — K-means cluster labels

Route order is significant: literal ``/customer/embed-all`` and
``/customer/segments`` must register after the ``/customer/{id}`` routes
to avoid FastAPI capturing the path-param form first.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.schemas.common import fail, ok
from app.services.ai import EmbeddingService

logger = logging.getLogger(__name__)


router = APIRouter(tags=["ai"])


@router.post("/customer/{customer_id}/embed")
async def embed_customer(
    customer_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Generate and store embedding vector for a single customer."""
    from app.models.customer import Customer

    result = await db.execute(
        select(Customer).where(Customer.id == customer_id, Customer.deleted_at.is_(None))
    )
    customer = result.scalar_one_or_none()
    if customer is None:
        return fail("Customer not found", 404)

    embedding = await EmbeddingService.embed_customer({
        "name": customer.name,
        "industry": customer.industry or "",
        "notes": customer.notes or "",
    })
    customer.embedding = embedding
    await db.commit()
    return ok({"customer_id": customer_id, "dimensions": len(embedding)})


@router.get("/customer/{customer_id}/similar")
async def similar_customers(
    customer_id: int,
    top_k: int = 10,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Find similar customers based on embedding vector similarity."""
    from app.models.customer import Customer

    result = await db.execute(
        select(Customer).where(Customer.id == customer_id, Customer.deleted_at.is_(None))
    )
    customer = result.scalar_one_or_none()
    if customer is None:
        return fail("Customer not found", 404)
    if customer.embedding is None:
        return fail("Customer has no embedding, call POST embed first", 400)

    similar = await EmbeddingService.similar_customers(customer.embedding, db, top_k, exclude_id=customer_id)
    return ok(similar)


@router.get("/customer/similar/search")
async def search_similar_by_text(
    q: str = Query(...),
    top_k: int = 10,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Natural-language semantic search for similar customers."""
    similar = await EmbeddingService.similar_by_text(q, db, top_k)
    return ok(similar)


@router.post("/customer/embed-all")
async def embed_all_customers(
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Batch generate embeddings for all customers that lack them."""
    stats = await EmbeddingService.index_all(db)
    await db.commit()
    return ok(stats)


@router.get("/customer/segments")
async def customer_segments(
    n_clusters: int = 5,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """AI-driven customer segmentation via K-means clustering on embeddings."""
    result = await EmbeddingService.segment_customers(db, n_clusters)
    return ok(result)
