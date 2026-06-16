import asyncio, sys
sys.path.insert(0, "/home/ttdiy/aierp/backend")
from app.models import (  # noqa
    account, approval, audit, customer, document,
    finance, product, rbac, report, sales, transaction, user,
)
from app.database import async_session
from app.models.lead import Lead
from app.models.product import Product
from sqlalchemy import select, func

async def main():
    async with async_session() as db:
        n = await db.scalar(select(func.count(Lead.id)))
        print(f"leads total: {n}")
        # by priority
        r = await db.execute(select(Lead.priority, func.count(Lead.id)).group_by(Lead.priority))
        for pri, cnt in r:
            print(f"  {pri:8s} {cnt}")
        r = await db.execute(select(Lead.industry, func.count(Lead.id)).group_by(Lead.industry).order_by(func.count(Lead.id).desc()))
        print("by industry:")
        for ind, cnt in r:
            print(f"  {ind:25s} {cnt}")

asyncio.run(main())
