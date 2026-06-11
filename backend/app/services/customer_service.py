import datetime as dt
import re
import unicodedata
from datetime import datetime, timezone
from difflib import SequenceMatcher

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

COMPANY_SUFFIXES = (
    "limitedliabilitycompany",
    "jointstocklimitedcompany",
    "股份有限公司",
    "有限责任公司",
    "集团有限公司",
    "控股有限公司",
    "有限公司",
    "责任公司",
    "股份公司",
    "控股集团",
    "companylimited",
    "companyltd",
    "colimited",
    "corporation",
    "limited",
    "集团",
    "公司",
    "coltd",
    "ltd",
    "inc",
    "llc",
)
NAME_PUNCT_RE = re.compile(
    r"[\s\-_\.,，、。·•/\\|:：;；'\"“”‘’&＋+（）()\[\]【】{}<>《》]"
)
LEADING_CITY_SUFFIX_RE = re.compile(r"^([\u4e00-\u9fff]{2,6})市(?=[\u4e00-\u9fff])")


async def list_customers_query(
    db: AsyncSession,
    *,
    page: int,
    page_size: int,
    q: str | None = None,
    industry: str | None = None,
    level: str | None = None,
    region: str | None = None,
    source: str | None = None,
    customer_type: str | None = None,
    owner: str | None = None,
    credit_level: str | None = None,
    status: str | None = None,
    sort_by: str = "id",
    sort_order: str = "desc",
) -> dict:
    base = select(Customer).where(Customer.deleted_at.is_(None))
    count_base = select(func.count(Customer.id)).where(Customer.deleted_at.is_(None))

    if q:
        like = f"%{q}%"
        filt = or_(
            Customer.name.ilike(like),
            Customer.code.ilike(like),
            Customer.contact_person.ilike(like),
        )
        base = base.where(filt)
        count_base = count_base.where(filt)

    for col, val in [
        (Customer.industry, industry),
        (Customer.level, level),
        (Customer.customer_type, customer_type),
        (Customer.region, region),
        (Customer.source, source),
        (Customer.credit_level, credit_level),
        (Customer.owner, owner),
    ]:
        if val:
            base = base.where(col == val)
            count_base = count_base.where(col == val)

    # Support comma-separated status values (e.g. "vip,active")
    if status:
        statuses = [s.strip() for s in status.split(",") if s.strip()]
        if len(statuses) == 1:
            base = base.where(Customer.status == statuses[0])
            count_base = count_base.where(Customer.status == statuses[0])
        elif len(statuses) > 1:
            base = base.where(Customer.status.in_(statuses))
            count_base = count_base.where(Customer.status.in_(statuses))

    total = (await db.execute(count_base)).scalar() or 0

    sort_col = SORTABLE_COLUMNS.get(sort_by, Customer.id)
    if sort_order == "asc":
        base = base.order_by(sort_col.asc())
    else:
        base = base.order_by(sort_col.desc())

    rows = (
        (await db.execute(base.offset((page - 1) * page_size).limit(page_size)))
        .scalars()
        .all()
    )

    return {"list": rows, "total": total, "page": page, "page_size": page_size}


async def get_customer(db: AsyncSession, customer_id: int) -> Customer | None:
    result = await db.execute(
        select(Customer).where(
            Customer.id == customer_id, Customer.deleted_at.is_(None)
        )
    )
    return result.scalar_one_or_none()


def calc_lifecycle(
    customer: Customer,
    order_count: int,
    last_order_date: datetime | None,
    now: datetime,
) -> str:
    created_at = customer.created_at
    created_days = (
        (now - created_at.replace(tzinfo=timezone.utc)).days if created_at else 0
    )
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
    created_days = (
        (now - created_at.replace(tzinfo=timezone.utc)).days if created_at else 0
    )
    score = 50

    # Recency (max +20)
    if orders:
        latest = max(
            o.created_at.replace(tzinfo=timezone.utc) for o in orders if o.created_at
        )
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
            lc = (
                last_contact
                if last_contact.tzinfo
                else last_contact.replace(tzinfo=timezone.utc)
            )
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
    label = (
        "优秀"
        if score >= 80
        else "良好"
        if score >= 60
        else "一般"
        if score >= 40
        else "差"
    )
    return score, label


def normalize_name(name: str | None) -> str:
    value = unicodedata.normalize("NFKC", (name or "").strip()).lower()
    value = re.sub(r"（[^）]*）|\([^)]*\)", "", value)
    value = NAME_PUNCT_RE.sub("", value)
    value = LEADING_CITY_SUFFIX_RE.sub(r"\1", value)
    for suffix in sorted(COMPANY_SUFFIXES, key=len, reverse=True):
        while value.endswith(suffix) and len(value) > len(suffix):
            value = value[: -len(suffix)]
    return value


def customer_name_conflict_message(name: str, conflict_name: str | None) -> str:
    return (
        f"客户名称已存在：{name} 与 {conflict_name or '-'} 归一后相同，请变更后再添加"
    )


async def find_name_conflict(
    db: AsyncSession,
    name: str | None,
    exclude_id: int | None = None,
) -> Customer | None:
    normalized = normalize_name(name)
    if not normalized:
        return None

    stmt = select(Customer).where(
        Customer.deleted_at.is_(None), Customer.name.isnot(None)
    )
    if exclude_id is not None:
        stmt = stmt.where(Customer.id != exclude_id)
    rows = (await db.execute(stmt)).scalars().all()
    return next((row for row in rows if normalize_name(row.name) == normalized), None)


def _normalize_contact_value(value: str | None) -> str:
    return unicodedata.normalize("NFKC", (value or "").strip()).lower()


def _normalize_email(value: str | None) -> str:
    return _normalize_contact_value(value)


def _normalize_phone(value: str | None) -> str:
    digits = re.sub(r"\D", "", value or "")
    return digits if len(digits) >= 7 else ""


def _name_similarity(a: str, b: str) -> float:
    if not a or not b:
        return 0
    if a == b:
        return 1
    return SequenceMatcher(None, a, b).ratio()


def _same_non_empty(a: str | None, b: str | None) -> bool:
    return bool(a and b and a == b)


def _names_are_related(name_a: str, name_b: str, similarity: float) -> bool:
    if similarity >= 0.72:
        return True
    shorter, longer = sorted((name_a, name_b), key=len)
    return len(shorter) >= 4 and shorter in longer


def _duplicate_reasons(
    a: Customer, b: Customer, name_a: str, name_b: str, threshold: float
) -> tuple[float, list[str]]:
    similarity = _name_similarity(name_a, name_b)
    reasons: list[str] = []

    code_match = _same_non_empty(
        _normalize_contact_value(a.code), _normalize_contact_value(b.code)
    )
    email_match = _same_non_empty(_normalize_email(a.email), _normalize_email(b.email))
    phone_match = _same_non_empty(_normalize_phone(a.phone), _normalize_phone(b.phone))
    short_name_match = _same_non_empty(
        normalize_name(a.short_name), normalize_name(b.short_name)
    )
    contact_match = _same_non_empty(
        _normalize_contact_value(a.contact_person),
        _normalize_contact_value(b.contact_person),
    )
    names_related = _names_are_related(name_a, name_b, similarity)

    if name_a and name_a == name_b and len(name_a) >= 3:
        reasons.append("名称完全一致")
        similarity = 1
    elif similarity >= max(threshold, 0.96):
        reasons.append("名称高度相似")

    if code_match:
        reasons.append("客户编码一致")
        similarity = max(similarity, 0.98)

    unique_reasons = []
    if email_match:
        unique_reasons.append("邮箱一致")
    if phone_match:
        unique_reasons.append("电话一致")
    if unique_reasons and names_related:
        reasons.extend(unique_reasons)
        similarity = max(similarity, 0.93)

    if similarity >= threshold:
        if short_name_match:
            reasons.append("简称一致")
        if contact_match:
            reasons.append("联系人一致")

    if not reasons:
        return similarity, []
    if reasons == ["名称高度相似"] and similarity < max(threshold, 0.96):
        return similarity, []
    return round(similarity, 3), list(dict.fromkeys(reasons))


def detect_duplicates(rows: list[Customer], threshold: float = 0.9) -> list[dict]:
    """Find duplicate customers using strict name matching plus identity evidence."""
    pairs = []
    threshold = max(0.9, min(threshold, 1.0))
    norm_map = {c.id: normalize_name(c.name) for c in rows}

    for i, a in enumerate(rows):
        na = norm_map[a.id]
        if len(na) < 3:
            continue
        for j in range(i + 1, len(rows)):
            nb = norm_map[rows[j].id]
            if len(nb) < 3:
                continue
            sim, reasons = _duplicate_reasons(a, rows[j], na, nb, threshold)
            if not reasons:
                continue
            pairs.append(
                {
                    "similarity": sim,
                    "reasons": reasons,
                    "customer_a": {
                        "id": a.id,
                        "name": a.name,
                        "phone": a.phone,
                        "owner": a.owner,
                    },
                    "customer_b": {
                        "id": rows[j].id,
                        "name": rows[j].name,
                        "phone": rows[j].phone,
                        "owner": rows[j].owner,
                    },
                }
            )

    pairs.sort(key=lambda x: (-x["similarity"], -len(x["reasons"])))
    return pairs[:30]


async def detect_duplicates_embedding(
    db, threshold: float = 0.85, top_k: int = 30
) -> list[dict]:
    """Find potential duplicates by pgvector cosine similarity. Requires embeddings to exist."""
    from sqlalchemy import select

    result = await db.execute(
        select(Customer).where(
            Customer.embedding.isnot(None), Customer.deleted_at.is_(None)
        )
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
                pairs.append(
                    {
                        "similarity": s["similarity"],
                        "customer_a": {
                            "id": c.id,
                            "name": c.name,
                            "phone": c.phone,
                            "owner": c.owner,
                        },
                        "customer_b": {
                            "id": s["id"],
                            "name": s["name"],
                            "phone": other.phone if other else None,
                            "owner": other.owner if other else None,
                        },
                    }
                )

    pairs.sort(key=lambda x: -x["similarity"])
    return pairs[:top_k]
