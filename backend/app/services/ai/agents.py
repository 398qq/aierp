"""AI Agents — each business domain has a specialized agent with structured output."""

import logging
from collections.abc import AsyncGenerator

from sqlalchemy import select

from app.services.ai.client import ai_client
from app.services.ai.prompts import (
    CUSTOMER_AGENT_SYSTEM,
    INVENTORY_AGENT_SYSTEM,
    PRODUCT_AGENT_SYSTEM,
    alert_enrichment_prompt,
    bom_parse_prompt,
    churn_risk_prompt,
    followup_analysis_prompt,
    followup_suggestion_prompt,
    product_parse_prompt,
    rfm_prompt,
    substitute_prompt,
)

logger = logging.getLogger(__name__)


class CustomerAgent:
    """Analyzes customer data and provides insights."""

    @staticmethod
    async def rfm_analysis(customer_data: dict) -> dict:
        schema = {
            "r_score": "integer 1-5",
            "f_score": "integer 1-5",
            "m_score": "integer 1-5",
            "tier": "string: 重要价值/重要发展/重要保持/一般价值/流失风险",
            "suggestion": "string",
        }
        try:
            result = await ai_client.chat_structured(
                [
                    {"role": "system", "content": CUSTOMER_AGENT_SYSTEM},
                    {"role": "user", "content": rfm_prompt(customer_data)},
                ],
                schema,
            )
            return result
        except Exception as e:
            logger.error(f"RFM analysis failed: {e}")
            return {"r_score": 3, "f_score": 3, "m_score": 3, "tier": "未分析", "suggestion": "AI分析暂时不可用"}

    @staticmethod
    async def churn_risk(customer_data: dict) -> dict:
        schema = {
            "risk_score": "integer 0-100",
            "risk_level": "string: 低/中/高",
            "factors": "list of strings",
            "recommendation": "string",
        }
        try:
            result = await ai_client.chat_structured(
                [
                    {"role": "system", "content": CUSTOMER_AGENT_SYSTEM},
                    {"role": "user", "content": churn_risk_prompt(customer_data)},
                ],
                schema,
            )
            return result
        except Exception as e:
            logger.error(f"Churn risk analysis failed: {e}")
            return {"risk_score": 0, "risk_level": "未知", "factors": [], "recommendation": "AI分析暂时不可用"}

    @staticmethod
    async def followup_suggestion(customer_data: dict) -> dict:
        schema = {
            "topic": "string",
            "recommended_products": "list of strings",
            "risk_points": "list of strings",
        }
        try:
            result = await ai_client.chat_structured(
                [
                    {"role": "system", "content": CUSTOMER_AGENT_SYSTEM},
                    {"role": "user", "content": followup_suggestion_prompt(customer_data)},
                ],
                schema,
            )
            return result
        except Exception as e:
            logger.error(f"Followup suggestion failed: {e}")
            return {"topic": "", "recommended_products": [], "risk_points": []}

    @staticmethod
    async def analyze_followups(followups: list[dict], customer_name: str = "") -> dict:
        """Semantic analysis of follow-up records: sentiment, topics, action items, risk signals."""
        schema = {
            "sentiment": "string: 积极/中性/消极",
            "sentiment_reason": "string",
            "key_topics": "list of strings (max 5)",
            "action_items": "list of strings",
            "risk_signals": "list of strings",
            "summary": "string (2-3 sentences)",
        }
        text = "\n".join(
            f"- [{f.get('method', '')}] {f.get('content', '')} (结果: {f.get('result', '无')})"
            for f in followups[-20:]  # Last 20 followups
        )
        if not text.strip():
            return {
                "sentiment": "中性", "sentiment_reason": "无跟进记录",
                "key_topics": [], "action_items": [], "risk_signals": [],
                "summary": "暂无跟进记录可供分析",
            }
        try:
            result = await ai_client.chat_structured(
                [
                    {"role": "system", "content": CUSTOMER_AGENT_SYSTEM},
                    {"role": "user", "content": followup_analysis_prompt(text, customer_name)},
                ],
                schema,
            )
            return result
        except Exception as e:
            logger.error(f"Followup analysis failed: {e}")
            return {
                "sentiment": "中性", "sentiment_reason": "AI分析失败",
                "key_topics": [], "action_items": [], "risk_signals": [],
                "summary": "AI分析暂时不可用",
            }

    @staticmethod
    async def enrich_alert(alert_context: dict) -> dict:
        """Generate AI action suggestions and templates for an alert event."""
        schema = {
            "followup_method": "string: 电话/邮件/拜访",
            "followup_timing": "string: when to contact",
            "talking_points": "list of strings (2-3)",
            "message_template": "string: ready-to-use message",
            "worst_case": "string",
        }
        try:
            result = await ai_client.chat_structured(
                [
                    {"role": "system", "content": CUSTOMER_AGENT_SYSTEM},
                    {"role": "user", "content": alert_enrichment_prompt(alert_context)},
                ],
                schema,
            )
            return result
        except Exception as e:
            logger.error(f"Alert enrichment failed: {e}")
            return {
                "followup_method": "电话", "followup_timing": "尽快",
                "talking_points": [], "message_template": "",
                "worst_case": "AI分析暂时不可用",
            }

    @staticmethod
    async def chat(query: str, context: str = "", model: str | None = None) -> AsyncGenerator[str, None]:
        messages = [{"role": "system", "content": f"{CUSTOMER_AGENT_SYSTEM}\n\n当前上下文：{context}"}]
        messages.append({"role": "user", "content": query})
        async for chunk in ai_client.chat_stream(messages, model=model):
            yield chunk


class EmbeddingService:
    """Vector embeddings for semantic customer search — backed by pgvector."""

    @staticmethod
    async def embed_customer(customer_data: dict) -> list[float]:
        """Build rich embedding from key customer fields."""
        parts = [
            f"客户：{customer_data.get('name')}",
            f"行业：{customer_data.get('industry', '')}",
            f"区域：{customer_data.get('region', '')}",
            f"类型：{customer_data.get('customer_type', '')}",
            f"等级：{customer_data.get('level', '')}",
            f"信用等级：{customer_data.get('credit_level', '')}",
            f"来源：{customer_data.get('source', '')}",
            f"备注：{customer_data.get('notes', '')}",
        ]
        return await ai_client.embed_single("，".join(parts))

    @staticmethod
    async def embed_product(product_data: dict) -> list[float]:
        text = f"型号：{product_data.get('part_number')}，描述：{product_data.get('description', '')}，品牌：{product_data.get('brand_name', '')}"
        return await ai_client.embed_single(text)

    @staticmethod
    async def similar_customers(embedding: list[float], db_session, top_k: int = 10, exclude_id: int | None = None) -> list:
        """pgvector cosine-distance search — runs entirely in PostgreSQL."""
        from sqlalchemy import select

        from app.models.customer import Customer

        cond = [Customer.embedding.isnot(None), Customer.deleted_at.is_(None)]
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
                "similarity": round(1 - float(r[4]), 4),  # distance → similarity
            }
            for r in rows
        ]

    @staticmethod
    async def similar_by_text(query: str, db_session, top_k: int = 10) -> list:
        """Search similar customers by natural-language query."""
        embedding = await ai_client.embed_single(query)
        return await EmbeddingService.similar_customers(embedding, db_session, top_k)

    @staticmethod
    async def index_all(db_session, batch_size: int = 50) -> dict:
        """Generate and store embeddings for all customers that lack them. Returns {indexed, skipped, errors}."""
        from sqlalchemy import select

        from app.models.customer import Customer

        result = await db_session.execute(
            select(Customer).where(Customer.deleted_at.is_(None), Customer.embedding.is_(None))
        )
        customers = result.scalars().all()

        indexed, errors = 0, 0
        for i in range(0, len(customers), batch_size):
            batch = customers[i : i + batch_size]
            texts = [
                f"客户：{c.name}，行业：{c.industry or ''}，区域：{c.region or ''}，"
                f"类型：{c.customer_type or ''}，等级：{c.level or ''}，"
                f"信用等级：{c.credit_level or ''}，来源：{c.source or ''}，备注：{c.notes or ''}"
                for c in batch
            ]
            try:
                embeddings = await ai_client.embed(texts)
                for c, emb in zip(batch, embeddings):
                    c.embedding = emb
                indexed += len(batch)
                await db_session.flush()
            except Exception:
                logger.exception(f"Embed batch {i // batch_size} failed")
                errors += len(batch)

        return {"indexed": indexed, "skipped": len(customers) - indexed - errors, "errors": errors}

    @staticmethod
    async def segment_customers(db_session, n_clusters: int = 5) -> dict:
        """K-means clustering on customer embeddings, with LLM-generated cluster labels.

        Returns {clusters: [{id, label, size, avg_similarity, sample_names}]}
        """
        import random
        from collections import defaultdict

        from app.models.customer import Customer

        result = await db_session.execute(
            select(Customer.id, Customer.name, Customer.embedding, Customer.industry, Customer.level)
            .where(Customer.embedding.isnot(None), Customer.deleted_at.is_(None))
        )
        rows = result.all()
        if len(rows) < n_clusters:
            return {"clusters": [], "error": f"Need at least {n_clusters} customers with embeddings"}

        embeddings = [r[2] for r in rows]
        dim = len(embeddings[0])

        # K-means++ initialization
        centroids = [random.choice(embeddings)[:]]
        for _ in range(1, n_clusters):
            dists = [min(_euclidean_sq(e, c) for c in centroids) for e in embeddings]
            total = sum(dists)
            pick = random.random() * total
            acc = 0
            for i, d in enumerate(dists):
                acc += d
                if acc >= pick:
                    centroids.append(embeddings[i][:])
                    break

        # Run K-means
        labels = [0] * len(rows)
        for _ in range(30):
            changed = False
            for i, e in enumerate(embeddings):
                best = min(range(n_clusters), key=lambda j: _euclidean_sq(e, centroids[j]))
                if best != labels[i]:
                    labels[i] = best
                    changed = True
            if not changed:
                break
            # Update centroids
            for j in range(n_clusters):
                members = [embeddings[i] for i, lbl in enumerate(labels) if lbl == j]
                if members:
                    centroids[j] = [sum(x[d] for x in members) / len(members) for d in range(dim)]

        # Build clusters
        clusters = defaultdict(list)
        for i, r in enumerate(rows):
            clusters[labels[i]].append({
                "id": r[0], "name": r[1], "industry": r[3], "level": r[4],
            })

        # Compute avg intra-cluster similarity and pick top samples
        result_clusters = []
        for j, members in clusters.items():
            centroid = centroids[j]
            avg_sim = 0.0
            for e in [embeddings[i] for i, lbl in enumerate(labels) if lbl == j]:
                avg_sim += 1 - _euclidean_sq(e, centroid) ** 0.5 / dim
            avg_sim = round(avg_sim / len(members), 4) if members else 0

            # Pick top-5 representative samples nearest centroid
            sorted_members = sorted(members, key=lambda m: _euclidean_sq(
                embeddings[next(i for i, r in enumerate(rows) if r[0] == m["id"])], centroid
            ))
            sample_names = [m["name"] for m in sorted_members[:5]]

            common_industry = max(set(m["industry"] for m in members), key=lambda x: sum(1 for m in members if m["industry"] == x))
            common_level = max(set(m["level"] for m in members), key=lambda x: sum(1 for m in members if m["level"] == x))

            result_clusters.append({
                "id": j,
                "size": len(members),
                "avg_similarity": avg_sim,
                "sample_names": sample_names,
                "common_industry": common_industry,
                "common_level": common_level,
                "label": f"群组{j + 1} ({common_industry or '未知行业'}·{common_level or '未知等级'})",
            })

        result_clusters.sort(key=lambda x: -x["size"])
        return {"clusters": result_clusters, "total": len(rows)}


def _euclidean_sq(a: list[float], b: list[float]) -> float:
    return sum((x - y) ** 2 for x, y in zip(a, b))


class InventoryAgent:
    """Analyzes inventory data and provides stock recommendations."""

    @staticmethod
    async def analyze(inventory_data: list[dict]) -> dict:
        schema = {
            "urgent_purchases": "list of dicts: {product_name, current_stock, safety_stock, suggested_qty, reason}",
            "slow_moving": "list of dicts: {product_name, stock, days_untouched, suggestion}",
            "stockout_risks": "list of dicts: {product_name, current_stock, monthly_usage, months_remaining, suggestion}",
            "overall_assessment": "string",
        }
        try:
            import json
            data_text = json.dumps(inventory_data, ensure_ascii=False, default=str)
            result = await ai_client.chat_structured(
                [
                    {"role": "system", "content": INVENTORY_AGENT_SYSTEM},
                    {"role": "user", "content": f"分析以下库存数据，给出采购建议和预警：\n{data_text}"},
                ],
                schema,
            )
            return result
        except Exception as e:
            logger.error(f"Inventory analysis failed: {e}")
            return {
                "urgent_purchases": [],
                "slow_moving": [],
                "stockout_risks": [],
                "overall_assessment": f"AI分析暂时不可用: {e}",
            }


class ProductAgent:
    """AI-powered product data extraction, BOM parsing, and substitute matching."""

    @staticmethod
    async def parse_product(raw_text: str) -> dict:
        """Extract structured product fields from unstructured text."""
        schema = {
            "name": "string: standardized product name",
            "sku": "string | null",
            "category": "string: 电容/电阻/IC/连接器/电感/二三极管/晶振/其他",
            "package_type": "string | null",
            "specs": "object: key-value parameter pairs",
            "brand_name": "string | null",
            "unit": "string | null",
            "description": "string: one-line summary",
        }
        try:
            return await ai_client.chat_structured(
                [
                    {"role": "system", "content": PRODUCT_AGENT_SYSTEM},
                    {"role": "user", "content": product_parse_prompt(raw_text)},
                ],
                schema,
            )
        except Exception as e:
            logger.error(f"Product parse failed: {e}")
            return {"name": "", "sku": None, "category": None, "package_type": None,
                    "specs": {}, "brand_name": None, "unit": None, "description": f"解析失败: {e}"}

    @staticmethod
    async def parse_bom(bom_text: str) -> list[dict]:
        """Parse a BOM list into an array of product entries."""
        schema = {
            "items": "list of dicts: {line_no, customer_pn, mfr_pn, description, reference, quantity, package, category}"
        }
        try:
            result = await ai_client.chat_structured(
                [
                    {"role": "system", "content": PRODUCT_AGENT_SYSTEM},
                    {"role": "user", "content": bom_parse_prompt(bom_text)},
                ],
                schema,
            )
            return result.get("items", [])
        except Exception as e:
            logger.error(f"BOM parse failed: {e}")
            return []

    @staticmethod
    async def suggest_substitutes(product_info: dict) -> dict:
        """Recommend substitute parts based on product specs."""
        schema = {
            "direct_substitutes": "list of strings: pin-to-pin compatible alternatives",
            "functional_substitutes": "list of strings: functionally equivalent alternatives",
            "verification_notes": "list of strings: things to verify before substitution",
        }
        try:
            return await ai_client.chat_structured(
                [
                    {"role": "system", "content": PRODUCT_AGENT_SYSTEM},
                    {"role": "user", "content": substitute_prompt(product_info)},
                ],
                schema,
            )
        except Exception as e:
            logger.error(f"Substitute suggestion failed: {e}")
            return {"direct_substitutes": [], "functional_substitutes": [], "verification_notes": [f"AI分析失败: {e}"]}
