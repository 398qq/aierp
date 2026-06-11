"""Embedding Pipeline — auto-generate entity embeddings on every save.

Fire-and-forget background embedding generation. Guarded by EMBEDDING_PIPELINE
env var so tests can disable it. Failures never propagate to the caller.
"""

import asyncio
import logging
import os

from app.database import async_session

logger = logging.getLogger(__name__)

_ENABLED = os.getenv("EMBEDDING_PIPELINE", "1") != "0"


def after_customer_save(customer_id: int):
    if not _ENABLED:
        return
    asyncio.create_task(_bg_embed_customer(customer_id))


def after_product_save(product_id: int):
    if not _ENABLED:
        return
    asyncio.create_task(_bg_embed_product(product_id))


def after_supplier_save(supplier_id: int):
    if not _ENABLED:
        return
    asyncio.create_task(_bg_embed_supplier(supplier_id))


async def _bg_embed_customer(customer_id: int):
    try:
        from app.models.customer import Customer
        from app.services.ai import EmbeddingService

        async with async_session() as db:
            c = await db.get(Customer, customer_id)
            if not c or c.deleted_at:
                return
            data = {
                "name": c.name,
                "industry": c.industry,
                "region": c.region,
                "customer_type": c.customer_type,
                "level": c.level,
                "credit_level": c.credit_level,
                "source": c.source,
                "notes": c.notes,
            }
            emb = await EmbeddingService.embed_customer(data)
            if emb:
                c.embedding = emb
                await db.commit()
    except Exception:
        # Always log at ERROR level so log-based alerting can catch it.
        # Failures are non-blocking by design (fire-and-forget pipeline).
        logger.error(
            "bg_embed_customer failed for id=%s — embedding skipped",
            customer_id,
            exc_info=True,
        )


async def _bg_embed_product(product_id: int):
    try:
        from app.models.product import Product
        from app.services.ai import EmbeddingService

        async with async_session() as db:
            p = await db.get(Product, product_id)
            if not p or p.deleted_at:
                return
            data = {"part_number": p.sku, "description": p.name, "brand_name": ""}
            emb = await EmbeddingService.embed_product(data)
            if emb:
                p.embedding = emb
                await db.commit()
    except Exception:
        logger.error(
            "bg_embed_product failed for id=%s — embedding skipped",
            product_id,
            exc_info=True,
        )


async def _bg_embed_supplier(supplier_id: int):
    try:
        from app.models.product import Supplier
        from app.services.ai import EmbeddingService

        async with async_session() as db:
            s = await db.get(Supplier, supplier_id)
            if not s or s.deleted_at:
                return
            data = {
                "name": s.name,
                "product_lines": s.product_lines,
                "supplier_type": s.supplier_type,
                "region": s.region,
                "certifications": s.certifications,
                "payment_terms": s.payment_terms,
                "financial_rating": s.financial_rating,
                "website": s.website,
                "notes": s.notes,
            }
            emb = await EmbeddingService.embed_supplier(data)
            if emb:
                s.embedding = emb
                await db.commit()
    except Exception:
        logger.error(
            "bg_embed_supplier failed for id=%s — embedding skipped",
            supplier_id,
            exc_info=True,
        )
