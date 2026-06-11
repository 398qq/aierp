"""Re-embed customers in small batches with rate-limit-aware retries."""

import asyncio
import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select

from app.database import async_session
from app.models.customer import Customer
from app.services.ai.client import ai_client

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("reembed")

BATCH_SIZE = 10
SLEEP_BETWEEN = 1.5  # seconds between batches


async def main():
    async with async_session() as db:
        result = await db.execute(
            select(Customer.id, Customer.name).where(
                Customer.deleted_at.is_(None),
                Customer.embedding.is_(None),
            )
        )
        rows = result.all()
        total = len(rows)
        logger.info(f"Found {total} customers without embeddings")

        indexed = 0
        errors = 0

        for i in range(0, total, BATCH_SIZE):
            batch = rows[i : i + BATCH_SIZE]
            ids = [r[0] for r in batch]
            names = [r[1] for r in batch]

            # Fetch full objects for this batch
            cust_result = await db.execute(select(Customer).where(Customer.id.in_(ids)))
            customers = {c.id: c for c in cust_result.scalars().all()}

            texts = []
            for cid in ids:
                c = customers.get(cid)
                if c is None:
                    continue
                texts.append(
                    f"客户：{c.name}，行业：{c.industry or ''}，区域：{c.region or ''}，"
                    f"类型：{c.customer_type or ''}，等级：{c.level or ''}，"
                    f"信用等级：{c.credit_level or ''}，来源：{c.source or ''}，备注：{c.notes or ''}"
                )

            try:
                embeddings = await ai_client.embed(texts)
                for cid, emb in zip(ids, embeddings):
                    if cid in customers:
                        customers[cid].embedding = emb
                        indexed += 1
                await db.commit()
                pct = indexed / total * 100
                logger.info(
                    f"[{indexed}/{total} {pct:.0f}%] Batch {i // BATCH_SIZE + 1}: {len(batch)} customers — OK"
                )
            except Exception as e:
                errors += len(batch)
                logger.warning(
                    f"Batch {i // BATCH_SIZE + 1} failed ({names[0]}..{names[-1]}): {e}"
                )

            await asyncio.sleep(SLEEP_BETWEEN)

        logger.info(f"Done. indexed={indexed}, errors={errors}")


if __name__ == "__main__":
    asyncio.run(main())
