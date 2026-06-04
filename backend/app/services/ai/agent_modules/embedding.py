"""Embedding Agent — vector embeddings and pgvector similarity search.

Encapsulates:
- Building embedding text from domain objects (customers, products, suppliers)
- Generating and storing embeddings in batch
- Cosine-similarity search via pgvector
- K-means clustering on customer embeddings

All public methods are async; the heavy K-means runs in a thread pool to
avoid blocking the event loop.
"""

import logging
from collections import defaultdict
import asyncio

from sqlalchemy import select

from app.services.ai.agent_modules.base import BaseAgent
from app.services.ai.client import ai_client

logger = logging.getLogger(__name__)


def _euclidean_sq(a: list[float], b: list[float]) -> float:
    return float(sum((x - y) ** 2 for x, y in zip(a, b)))


def _run_kmeans(
    embeddings: list[list[float]],
    n_clusters: int,
    n_iter: int = 30,
) -> tuple[list[int], list[list[float]]]:
    """Pure synchronous K-means++ on a list of embedding vectors.

    Returns (labels, centroids). Deterministic for given inputs + seed.
    """
    import random

    dim = len(embeddings[0])
    n = len(embeddings)

    rng = random.Random(42)
    centroids = [list(embeddings[rng.randrange(n)])]
    for _ in range(n_clusters - 1):
        dists = [min(_euclidean_sq(e, c) for c in centroids) for e in embeddings]
        total = sum(dists) or 1.0
        probs = [d / total for d in dists]
        centroids.append(list(embeddings[rng.choices(range(n), probs)[0]]))

    for _ in range(n_iter):
        labels = [
            min(range(len(centroids)), key=lambda j: _euclidean_sq(e, centroids[j]))
            for e in embeddings
        ]
        new_centroids = [[0.0] * dim for _ in range(len(centroids))]
        counts = [0] * len(centroids)
        for e, lbl in zip(embeddings, labels):
            for k in range(dim):
                new_centroids[lbl][k] += e[k]
            counts[lbl] += 1
        for j in range(len(centroids)):
            if counts[j] > 0:
                for k in range(dim):
                    new_centroids[j][k] /= counts[j]
            else:
                new_centroids[j] = list(centroids[j])
        if new_centroids == centroids:
            break
        centroids = new_centroids

    return labels, centroids


class EmbeddingService(BaseAgent):
    name = "embedding"
    description = "Vector embeddings and similarity search for customers, products, suppliers."

    # ---- Text builders ----

    @staticmethod
    def _customer_text(c: dict) -> str:
        parts = [
            f"客户：{c.get('name')}",
            f"行业：{c.get('industry', '')}",
            f"区域：{c.get('region', '')}",
            f"类型：{c.get('customer_type', '')}",
            f"等级：{c.get('level', '')}",
            f"信用等级：{c.get('credit_level', '')}",
            f"来源：{c.get('source', '')}",
            f"备注：{c.get('notes', '')}",
        ]
        return "，".join(parts)

    @staticmethod
    def _product_text(p: dict) -> str:
        return (
            f"型号：{p.get('part_number') or p.get('sku', '')}，"
            f"描述：{p.get('description') or p.get('name', '')}，"
            f"品牌：{p.get('brand_name', '')}"
        )

    @staticmethod
    def _supplier_text(s: dict) -> str:
        parts = [
            f"供应商：{s.get('name')}",
            f"产品线：{s.get('product_lines', '')}",
            f"类型：{s.get('supplier_type', '')}",
            f"区域：{s.get('region', '')}",
            f"认证：{s.get('certifications', '')}",
            f"付款条件：{s.get('payment_terms', '')}",
            f"财务评级：{s.get('financial_rating', '')}",
            f"网站：{s.get('website', '')}",
            f"备注：{s.get('notes', '')}",
        ]
        return "，".join(parts)

    # ---- Single embed calls ----

    @staticmethod
    async def embed_customer(customer_data: dict) -> list[float]:
        return await ai_client.embed_single(EmbeddingService._customer_text(customer_data))

    @staticmethod
    async def embed_product(product_data: dict) -> list[float]:
        return await ai_client.embed_single(EmbeddingService._product_text(product_data))

    @staticmethod
    async def embed_supplier(supplier_data: dict) -> list[float]:
        return await ai_client.embed_single(EmbeddingService._supplier_text(supplier_data))

    # ---- Similarity search ----

    @staticmethod
    async def similar_customers(
        embedding: list[float],
        db_session,
        top_k: int = 10,
        exclude_id: int | None = None,
    ) -> list[dict]:
        """pgvector cosine-distance search — runs entirely in PostgreSQL."""
        from app.models.customer import Customer

        cond: list = [Customer.embedding.isnot(None), Customer.deleted_at.is_(None)]
        if exclude_id is not None:
            cond.append(Customer.id != exclude_id)

        result = await db_session.execute(
            select(
                Customer.id, Customer.name, Customer.industry, Customer.region,
                Customer.embedding.cosine_distance(embedding).label("distance"),
            )
            .where(*cond)
            .order_by(Customer.embedding.cosine_distance(embedding))
            .limit(top_k)
        )
        rows = result.all()
        return [
            {
                "id": r[0], "name": r[1], "industry": r[2], "region": r[3],
                "similarity": round(1 - float(r[4]) / 2, 4),
            }
            for r in rows
        ]

    @staticmethod
    async def similar_by_text(query: str, db_session, top_k: int = 10) -> list[dict]:
        """Search similar customers by natural-language query."""
        embedding = await ai_client.embed_single(query)
        return await EmbeddingService.similar_customers(embedding, db_session, top_k)

    @staticmethod
    async def similar_suppliers(
        embedding: list[float],
        db_session,
        top_k: int = 10,
        exclude_id: int | None = None,
    ) -> list[dict]:
        from app.models.product import Supplier
        cond: list = [Supplier.embedding.isnot(None), Supplier.deleted_at.is_(None)]
        if exclude_id is not None:
            cond.append(Supplier.id != exclude_id)
        result = await db_session.execute(
            select(
                Supplier.id, Supplier.name, Supplier.product_lines, Supplier.region,
                Supplier.embedding.cosine_distance(embedding).label("distance"),
            )
            .where(*cond)
            .order_by(Supplier.embedding.cosine_distance(embedding))
            .limit(top_k)
        )
        rows = result.all()
        return [
            {
                "id": r[0], "name": r[1], "product_lines": r[2], "region": r[3],
                "similarity": round(1 - float(r[4]) / 2, 4),
            }
            for r in rows
        ]

    @staticmethod
    async def similar_suppliers_by_text(query: str, db_session, top_k: int = 10) -> list[dict]:
        embedding = await ai_client.embed_single(query)
        return await EmbeddingService.similar_suppliers(embedding, db_session, top_k)

    # ---- Batch indexing ----

    @staticmethod
    async def index_all_customers(db_session, batch_size: int = 50) -> dict:
        """Generate embeddings for all customers that lack them. Cursor-paginated."""
        from app.models.customer import Customer

        id_rows = (await db_session.execute(
            select(Customer.id).where(
                Customer.deleted_at.is_(None), Customer.embedding.is_(None)
            )
        )).scalars().all()

        indexed, errors = 0, 0
        total = len(id_rows)
        processed = 0

        while processed < total:
            batch_ids = id_rows[processed: processed + batch_size]
            batch = (await db_session.execute(
                select(Customer).where(Customer.id.in_(batch_ids))
            )).scalars().all()
            processed += len(batch_ids)

            texts = [
                EmbeddingService._customer_text({
                    "name": c.name, "industry": c.industry, "region": c.region,
                    "customer_type": c.customer_type, "level": c.level,
                    "credit_level": c.credit_level, "source": c.source, "notes": c.notes,
                })
                for c in batch
            ]
            try:
                embeddings = await ai_client.embed(texts)
                for c, emb in zip(batch, embeddings):
                    c.embedding = emb
                indexed += len(batch)
                await db_session.flush()
            except Exception:
                logger.exception("Embed customer batch offset %s failed", processed - batch_size)
                errors += len(batch)

        return {"indexed": indexed, "skipped": total - indexed - errors, "errors": errors}

    @staticmethod
    async def index_all_products(db_session, batch_size: int = 50) -> dict:
        from app.models.product import Product
        id_rows = (await db_session.execute(
            select(Product.id).where(
                Product.deleted_at.is_(None), Product.embedding.is_(None)
            )
        )).scalars().all()

        indexed, errors = 0, 0
        total = len(id_rows)
        processed = 0
        while processed < total:
            batch_ids = id_rows[processed: processed + batch_size]
            batch = (await db_session.execute(
                select(Product).where(Product.id.in_(batch_ids))
            )).scalars().all()
            processed += len(batch_ids)
            texts = [
                f"型号：{p.sku or ''}，名称：{p.name}，品类：{p.category or ''}，"
                f"规格：{p.specs or ''}，封装：{p.package_type or ''}，备注：{p.notes or ''}"
                for p in batch
            ]
            try:
                embeddings = await ai_client.embed(texts)
                for p, emb in zip(batch, embeddings):
                    p.embedding = emb
                indexed += len(batch)
                await db_session.flush()
            except Exception:
                logger.exception("Embed product batch offset %s failed", processed - batch_size)
                errors += len(batch)
        return {"indexed": indexed, "skipped": total - indexed - errors, "errors": errors}

    @staticmethod
    async def index_all_suppliers(db_session, batch_size: int = 50) -> dict:
        from app.models.product import Supplier
        id_rows = (await db_session.execute(
            select(Supplier.id).where(
                Supplier.deleted_at.is_(None), Supplier.embedding.is_(None)
            )
        )).scalars().all()
        indexed, errors = 0, 0
        total = len(id_rows)
        processed = 0
        while processed < total:
            batch_ids = id_rows[processed: processed + batch_size]
            batch = (await db_session.execute(
                select(Supplier).where(Supplier.id.in_(batch_ids))
            )).scalars().all()
            processed += len(batch_ids)
            texts = [
                f"供应商：{s.name}，产品线：{s.product_lines or ''}，"
                f"类型：{s.supplier_type or ''}，区域：{s.region or ''}，"
                f"认证：{s.certifications or ''}，付款条件：{s.payment_terms or ''}，"
                f"备注：{s.notes or ''}"
                for s in batch
            ]
            try:
                embeddings = await ai_client.embed(texts)
                for s, emb in zip(batch, embeddings):
                    s.embedding = emb
                indexed += len(batch)
                await db_session.flush()
            except Exception:
                logger.exception("Embed supplier batch offset %s failed", processed - batch_size)
                errors += len(batch)
        return {"indexed": indexed, "skipped": total - indexed - errors, "errors": errors}

    @staticmethod
    async def index_all(db_session, batch_size: int = 50) -> dict:
        """Index all entity types. Returns aggregated counts."""
        customers = await EmbeddingService.index_all_customers(db_session, batch_size)
        products = await EmbeddingService.index_all_products(db_session, batch_size)
        suppliers = await EmbeddingService.index_all_suppliers(db_session, batch_size)
        return {
            "customers": customers,
            "products": products,
            "suppliers": suppliers,
            "total_indexed": customers["indexed"] + products["indexed"] + suppliers["indexed"],
            "total_errors": customers["errors"] + products["errors"] + suppliers["errors"],
        }

    # ---- Clustering ----

    @staticmethod
    async def segment_customers(db_session, n_clusters: int = 5) -> dict:
        """K-means clustering on customer embeddings.

        Returns {"clusters": [...], "total": int}
        Each cluster has {id, size, avg_similarity, sample_names, label}.
        """
        from app.models.customer import Customer

        result = await db_session.execute(
            select(Customer.id, Customer.name, Customer.embedding, Customer.industry, Customer.level)
            .where(Customer.embedding.isnot(None), Customer.deleted_at.is_(None))
        )
        rows = result.all()
        if len(rows) < n_clusters:
            return {"clusters": [], "error": f"Need at least {n_clusters} customers with embeddings"}

        embeddings = [list(r[2]) for r in rows]
        labels, centroids = await asyncio.to_thread(_run_kmeans, embeddings, n_clusters)

        clusters: dict[int, list[dict]] = defaultdict(list)
        for i, r in enumerate(rows):
            clusters[labels[i]].append({
                "id": r[0], "name": r[1], "industry": r[3], "level": r[4],
            })

        # Map member id → its embedding index
        id_to_idx = {r[0]: i for i, r in enumerate(rows)}

        result_clusters: list[dict] = []
        for j, members in clusters.items():
            centroid = centroids[j]
            dim = len(centroid)
            member_embs = [embeddings[id_to_idx[m["id"]]] for m in members]
            avg_sim = (
                sum(1 - _euclidean_sq(e, centroid) ** 0.5 / dim for e in member_embs)
                / len(members)
                if members else 0
            )
            avg_sim = round(avg_sim, 4)

            sorted_members = sorted(
                members,
                key=lambda m: _euclidean_sq(embeddings[id_to_idx[m["id"]]], centroid),
            )
            sample_names = [m["name"] for m in sorted_members[:5]]

            industries = [m["industry"] for m in members]
            levels = [m["level"] for m in members]
            common_industry = max(set(industries), key=lambda x: industries.count(x)) if industries else None
            common_level = max(set(levels), key=lambda x: levels.count(x)) if levels else None

            result_clusters.append({
                "id": j,
                "size": len(members),
                "avg_similarity": avg_sim,
                "sample_names": sample_names,
                "common_industry": common_industry,
                "common_level": common_level,
                "label": f"群组{j + 1} ({common_industry or '未知行业'}·{common_level or '未知等级'})",
            })

        result_clusters.sort(key=lambda x: -int(x["size"]))
        return {"clusters": result_clusters, "total": len(rows)}
