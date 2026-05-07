import datetime as dt
import re
from datetime import datetime, timezone

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer import Customer
from app.services.ai.agents import EmbeddingService

SORTABLE_COLUMNS: dict[str, any] = {
    "id": Customer.id,
    "name": Customer.name,
    "code": Customer.code,
    "industry": Customer.industry,
    "level": Customer.level,
    "region": Customer.region,
    "source": Customer.source,
    "credit_level": Customer.credit_level,
    "created_at": Customer.created_at,
    "last_contacted_at": Customer.last_contacted_at,
}


async def list_customers_query(
    db: AsyncSession, *,
    page: int, page_size: int,
    q: str | None = None,
    industry: str | None = None,
    level: str | None = None,
    region: str | None = None,
    source: str | None = None,
    customer_type: str | None = None,
    owner: str | None = None,
    credit_level: str | None = None,
    sort_by: str = "id",
    sort_order: str = "desc",
) -> dict:
    base = select(Customer).where(Customer.deleted_at.is_(None))
    count_base = select(func.count(Customer.id)).where(Customer.deleted_at.is_(None))

    if q:
        like = f"%{q}%"
        filt = or_(Customer.name.ilike(like), Customer.code.ilike(like), Customer.contact_person.ilike(like))
        base = base.where(filt)
        count_base = count_base.where(filt)

    for col, val in [
        (Customer.industry, industry), (Customer.level, level),
        (Customer.customer_type, customer_type), (Customer.region, region),
        (Customer.source, source), (Customer.credit_level, credit_level),
        (Customer.owner, owner),
    ]:
        if val:
            base = base.where(col == val)
            count_base = count_base.where(col == val)

    total = (await db.execute(count_base)).scalar() or 0

    sort_col = SORTABLE_COLUMNS.get(sort_by, Customer.id)
    if sort_order == "asc":
        base = base.order_by(sort_col.asc())
    else:
        base = base.order_by(sort_col.desc())

    rows = (await db.execute(
        base.offset((page - 1) * page_size).limit(page_size)
    )).scalars().all()

    return {"list": rows, "total": total, "page": page, "page_size": page_size}


async def get_customer(db: AsyncSession, customer_id: int) -> Customer | None:
    result = await db.execute(
        select(Customer).where(Customer.id == customer_id, Customer.deleted_at.is_(None))
    )
    return result.scalar_one_or_none()


def calc_lifecycle(customer: Customer, order_count: int, last_order_date: datetime | None, now: datetime) -> str:
    created_at = customer.created_at
    created_days = (now - created_at.replace(tzinfo=timezone.utc)).days if created_at else 0
    if order_count == 0:
        return "新客户" if created_days <= 30 else "沉默客户"
    if last_order_date and last_order_date.tzinfo:
        days_since_last = (now - last_order_date).days
        if days_since_last <= 90:
            return "活跃"
        elif days_since_last <= 365:
            return "衰退"
    elif last_order_date:
        days_since_last = (now - last_order_date.replace(tzinfo=timezone.utc)).days
        if days_since_last <= 90:
            return "活跃"
        elif days_since_last <= 365:
            return "衰退"
    return "流失"


def calc_health(
    customer: Customer,
    orders: list,
    payments: list,
    now: datetime,
) -> tuple[int, str]:
    """Returns (score, label) for customer health. Score is 0-100."""
    created_at = customer.created_at
    created_days = (now - created_at.replace(tzinfo=timezone.utc)).days if created_at else 0
    score = 50

    # Recency (max +20)
    if orders:
        latest = max(o.created_at.replace(tzinfo=timezone.utc) for o in orders if o.created_at)
        days_since_last = (now - latest).days
        if days_since_last <= 30:
            score += 20
        elif days_since_last <= 90:
            score += 15
        elif days_since_last <= 180:
            score += 8
        elif days_since_last <= 365:
            score += 3
        else:
            score -= 5
    elif created_days > 90:
        score -= 10

    # Frequency (max +15)
    if created_days > 0 and orders:
        annual_rate = len(orders) / (created_days / 365)
        if annual_rate >= 12:
            score += 15
        elif annual_rate >= 6:
            score += 10
        elif annual_rate >= 2:
            score += 5
        elif annual_rate >= 1:
            score += 2

    # Credit usage (max +15)
    credit_limit = float(customer.credit_limit or 0)
    if credit_limit > 0:
        outstanding = sum(float(p.amount or 0) for p in payments if p.paid_at is None)
        ratio = outstanding / credit_limit
        if ratio < 0.2:
            score += 15
        elif ratio < 0.5:
            score += 10
        elif ratio < 0.8:
            score += 5
        elif ratio > 0.95:
            score -= 15
        else:
            score -= 5

    # Activity recency (max +10)
    last_contact = customer.last_contacted_at
    if last_contact:
        if isinstance(last_contact, dt.datetime):
            lc = last_contact if last_contact.tzinfo else last_contact.replace(tzinfo=timezone.utc)
        elif isinstance(last_contact, dt.date):
            lc = dt.datetime.combine(last_contact, dt.time.min, tzinfo=timezone.utc)
        else:
            lc = None
        if lc:
            days_since_contact = (now - lc).days
            if days_since_contact <= 30:
                score += 10
            elif days_since_contact <= 90:
                score += 5
            elif days_since_contact > 365:
                score -= 5

    # Level bonus
    if customer.level == "A":
        score += 5
    elif customer.level in ("C", "D"):
        score -= 5

    score = max(0, min(100, score))
    label = "优秀" if score >= 80 else "良好" if score >= 60 else "一般" if score >= 40 else "差"
    return score, label


def normalize_name(name: str) -> str:
    return re.sub(r'[（）\(\)\s\-_\.\,，、。有限公司有限责任控股集团分公司]', '', name or '').lower()


def detect_duplicates(rows: list[Customer], threshold: float = 0.7) -> list[dict]:
    """Find potential duplicate customers by name trigram overlap."""
    pairs = []
    norm_map = {c.id: normalize_name(c.name) for c in rows}

    for i, a in enumerate(rows):
        na = norm_map[a.id]
        if len(na) < 2:
            continue
        for j in range(i + 1, len(rows)):
            nb = norm_map[rows[j].id]
            if len(nb) < 2:
                continue
            common = len(set(na) & set(nb))
            longer = max(len(na), len(nb))
            if longer == 0:
                continue
            sim = common / longer
            if sim >= threshold:
                pairs.append({
                    "similarity": round(sim, 3),
                    "customer_a": {"id": a.id, "name": a.name, "phone": a.phone, "owner": a.owner},
                    "customer_b": {"id": rows[j].id, "name": rows[j].name, "phone": rows[j].phone, "owner": rows[j].owner},
                })

    pairs.sort(key=lambda x: -x["similarity"])
    return pairs[:30]


async def detect_duplicates_embedding(db, threshold: float = 0.85, top_k: int = 30) -> list[dict]:
    """Find potential duplicates by pgvector cosine similarity. Requires embeddings to exist."""
    from sqlalchemy import select

    result = await db.execute(
        select(Customer).where(Customer.embedding.isnot(None), Customer.deleted_at.is_(None))
    )
    customers = result.scalars().all()
    if len(customers) < 2:
        return []

    pairs = []
    seen: set[tuple[int, int]] = set()

    for c in customers:
        similar = await EmbeddingService.similar_customers(
            c.embedding, db, top_k=min(5, len(customers) - 1), exclude_id=c.id
        )
        for s in similar:
            pair_key = (min(c.id, s["id"]), max(c.id, s["id"]))
            if pair_key in seen:
                continue
            seen.add(pair_key)
            if s["similarity"] >= threshold:
                other = next((x for x in customers if x.id == s["id"]), None)
                pairs.append({
                    "similarity": s["similarity"],
                    "customer_a": {"id": c.id, "name": c.name, "phone": c.phone, "owner": c.owner},
                    "customer_b": {"id": s["id"], "name": s["name"], "phone": other.phone if other else None, "owner": other.owner if other else None},
                })

    pairs.sort(key=lambda x: -x["similarity"])
    return pairs[:top_k]
