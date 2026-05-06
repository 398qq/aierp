from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer import Customer


async def list_customers_query(db: AsyncSession, *, page: int, page_size: int, q: str | None = None, industry: str | None = None, level: str | None = None) -> dict:
    base = select(Customer).where(Customer.deleted_at.is_(None))
    count_base = select(func.count(Customer.id)).where(Customer.deleted_at.is_(None))

    if q:
        like = f"%{q}%"
        base = base.where(or_(Customer.name.ilike(like), Customer.code.ilike(like), Customer.contact_person.ilike(like)))
        count_base = count_base.where(or_(Customer.name.ilike(like), Customer.code.ilike(like), Customer.contact_person.ilike(like)))
    if industry:
        base = base.where(Customer.industry == industry)
        count_base = count_base.where(Customer.industry == industry)
    if level:
        base = base.where(Customer.level == level)
        count_base = count_base.where(Customer.level == level)

    total = (await db.execute(count_base)).scalar() or 0
    rows = (await db.execute(base.order_by(Customer.id.desc()).offset((page - 1) * page_size).limit(page_size))).scalars().all()

    return {"list": rows, "total": total, "page": page, "page_size": page_size}


async def get_customer(db: AsyncSession, customer_id: int) -> Customer | None:
    result = await db.execute(select(Customer).where(Customer.id == customer_id, Customer.deleted_at.is_(None)))
    return result.scalar_one_or_none()
