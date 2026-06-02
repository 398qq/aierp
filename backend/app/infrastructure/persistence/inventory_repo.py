"""Inventory repository — concurrency-safe stock reservation."""

import asyncio
import logging

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.observability.metrics import (
    inventory_concurrent_conflicts_total,
    inventory_reserved_total,
)
from app.domain.shared.errors import (
    ConcurrentModificationError,
    InsufficientStockError,
)
from app.models.product import Inventory

logger = logging.getLogger(__name__)


class InventoryRepository:
    """Inventory repository with optimistic locking via `version` column.

    All mutations go through CAS (compare-and-swap) on the version column.
    Callers must treat failures as retryable.

    Note: this repository does NOT call commit() — it relies on the
    surrounding Unit of Work (or test fixture) to manage the transaction.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(
        self,
        product_id: int,
        warehouse_id: int,
        for_update: bool = False,
    ) -> Inventory | None:
        stmt = select(Inventory).where(
            Inventory.product_id == product_id,
            Inventory.warehouse_id == warehouse_id,
            Inventory.deleted_at.is_(None),
        )
        if for_update:
            stmt = stmt.with_for_update()
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def reserve(
        self,
        product_id: int,
        warehouse_id: int,
        qty: int,
        max_retries: int = 3,
    ) -> bool:
        """Reserve stock using optimistic lock with retry.

        Returns True if reserved, False if insufficient stock.
        Raises ConcurrentModificationError if all retries fail.
        """
        if qty <= 0:
            raise ValueError("qty must be positive")

        for attempt in range(max_retries):
            inv = await self.get(product_id, warehouse_id)
            if inv is None:
                return False

            available = inv.quantity - inv.locked_quantity
            if available < qty:
                logger.info(
                    "Insufficient stock: product=%s wh=%s available=%s requested=%s",
                    product_id, warehouse_id, available, qty,
                )
                return False

            stmt = (
                update(Inventory)
                .where(
                    Inventory.id == inv.id,
                    Inventory.version == inv.version,
                    Inventory.quantity - Inventory.locked_quantity >= qty,
                )
                .values(
                    locked_quantity=Inventory.locked_quantity + qty,
                    version=Inventory.version + 1,
                )
            )
            result = await self.session.execute(stmt)
            if result.rowcount > 0:
                inventory_reserved_total.inc(product_category="unknown")
                await self.session.flush()
                return True

            inventory_concurrent_conflicts_total.inc()
            await asyncio.sleep(0.01 * (2 ** attempt))

        raise ConcurrentModificationError(
            f"无法预占库存 product={product_id} warehouse={warehouse_id}",
            product_id=product_id,
            warehouse_id=warehouse_id,
        )

    async def release(
        self,
        product_id: int,
        warehouse_id: int,
        qty: int,
        max_retries: int = 3,
    ) -> bool:
        """Release reserved stock (e.g. on order cancellation)."""
        if qty <= 0:
            raise ValueError("qty must be positive")

        for attempt in range(max_retries):
            inv = await self.get(product_id, warehouse_id)
            if inv is None:
                return False

            release_qty = min(qty, inv.locked_quantity)

            stmt = (
                update(Inventory)
                .where(
                    Inventory.id == inv.id,
                    Inventory.version == inv.version,
                )
                .values(
                    locked_quantity=Inventory.locked_quantity - release_qty,
                    version=Inventory.version + 1,
                )
            )
            result = await self.session.execute(stmt)
            if result.rowcount > 0:
                await self.session.flush()
                return True

            await asyncio.sleep(0.01 * (2 ** attempt))

        raise ConcurrentModificationError(
            f"无法释放库存 product={product_id} warehouse={warehouse_id}",
            product_id=product_id,
            warehouse_id=warehouse_id,
        )

    async def deduct(
        self,
        product_id: int,
        warehouse_id: int,
        qty: int,
        max_retries: int = 3,
    ) -> bool:
        """Deduct physical stock (and release lock) — used on shipment.

        Reduces both `locked_quantity` and `quantity` by `qty` (whichever locked
        portion exists first, then from free stock if needed).
        """
        if qty <= 0:
            raise ValueError("qty must be positive")

        for attempt in range(max_retries):
            inv = await self.get(product_id, warehouse_id)
            if inv is None:
                raise InsufficientStockError(product_id, qty, 0)

            if inv.quantity < qty:
                raise InsufficientStockError(
                    product_id, qty, inv.quantity,
                )

            release_lock = min(qty, inv.locked_quantity)

            stmt = (
                update(Inventory)
                .where(
                    Inventory.id == inv.id,
                    Inventory.version == inv.version,
                    Inventory.quantity >= qty,
                )
                .values(
                    quantity=Inventory.quantity - qty,
                    locked_quantity=Inventory.locked_quantity - release_lock,
                    version=Inventory.version + 1,
                )
            )
            result = await self.session.execute(stmt)
            if result.rowcount > 0:
                await self.session.flush()
                return True

            await asyncio.sleep(0.01 * (2 ** attempt))

        raise ConcurrentModificationError(
            f"无法扣减库存 product={product_id} warehouse={warehouse_id}",
            product_id=product_id,
            warehouse_id=warehouse_id,
        )

    async def receive(
        self,
        product_id: int,
        warehouse_id: int,
        qty: int,
        max_retries: int = 3,
    ) -> Inventory:
        """Add stock from inbound (e.g. PO receipt).

        Auto-creates the inventory row if missing. Uses optimistic lock on
        existing rows; new rows are inserted directly.
        """
        if qty <= 0:
            raise ValueError("qty must be positive")

        for attempt in range(max_retries):
            inv = await self.get(product_id, warehouse_id)
            if inv is None:
                new_inv = Inventory(
                    product_id=product_id,
                    warehouse_id=warehouse_id,
                    quantity=qty,
                    locked_quantity=0,
                    version=0,
                )
                self.session.add(new_inv)
                try:
                    await self.session.flush()
                    return new_inv
                except Exception:
                    # Another process created it concurrently — retry
                    await self.session.rollback()
                    await asyncio.sleep(0.01 * (2 ** attempt))
                    continue

            stmt = (
                update(Inventory)
                .where(
                    Inventory.id == inv.id,
                    Inventory.version == inv.version,
                )
                .values(
                    quantity=Inventory.quantity + qty,
                    version=Inventory.version + 1,
                )
            )
            result = await self.session.execute(stmt)
            if result.rowcount > 0:
                await self.session.flush()
                await self.session.refresh(inv)
                return inv

            await asyncio.sleep(0.01 * (2 ** attempt))

        raise ConcurrentModificationError(
            f"无法入库 product={product_id} warehouse={warehouse_id}",
            product_id=product_id,
            warehouse_id=warehouse_id,
        )
