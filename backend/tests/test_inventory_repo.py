"""Tests for InventoryRepository — optimistic locking and stock operations."""

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domain.shared.errors import (
    ConcurrentModificationError,
    InsufficientStockError,
)
from app.infrastructure.persistence.inventory_repo import InventoryRepository
from app.models.product import Inventory, Product, Warehouse


pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def inventory_session(engine, create_tables):
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session


@pytest_asyncio.fixture
async def sample_inventory(inventory_session):
    wh = Warehouse(name="Main WH")
    product = Product(sku="TEST-001", name="Test Product")
    inventory_session.add_all([wh, product])
    await inventory_session.flush()
    inv = Inventory(
        product_id=product.id,
        warehouse_id=wh.id,
        quantity=100,
        locked_quantity=0,
        version=0,
    )
    inventory_session.add(inv)
    await inventory_session.commit()
    return product, wh, inv


class TestInventoryRepositoryReserve:
    async def test_reserve_increments_locked(self, inventory_session, sample_inventory):
        product, wh, inv = sample_inventory
        repo = InventoryRepository(inventory_session)

        ok = await repo.reserve(product.id, wh.id, 30)
        await inventory_session.commit()

        assert ok is True
        await inventory_session.refresh(inv)
        assert inv.locked_quantity == 30
        assert inv.quantity == 100
        assert inv.version == 1

    async def test_reserve_returns_false_when_insufficient(
        self, inventory_session, sample_inventory
    ):
        product, wh, inv = sample_inventory
        repo = InventoryRepository(inventory_session)

        ok = await repo.reserve(product.id, wh.id, 999)
        await inventory_session.commit()

        assert ok is False
        await inventory_session.refresh(inv)
        assert inv.locked_quantity == 0
        assert inv.version == 0  # No update happened

    async def test_reserve_returns_false_for_nonexistent(self, inventory_session):
        repo = InventoryRepository(inventory_session)
        ok = await repo.reserve(product_id=9999, warehouse_id=1, qty=1)
        assert ok is False

    async def test_reserve_rejects_non_positive(self, inventory_session):
        repo = InventoryRepository(inventory_session)
        with pytest.raises(ValueError):
            await repo.reserve(1, 1, 0)
        with pytest.raises(ValueError):
            await repo.reserve(1, 1, -5)


class TestInventoryRepositoryRelease:
    async def test_release_decrements_locked(self, inventory_session, sample_inventory):
        product, wh, inv = sample_inventory
        inv.locked_quantity = 40
        inv.version = 1
        await inventory_session.commit()

        repo = InventoryRepository(inventory_session)
        ok = await repo.release(product.id, wh.id, 15)
        await inventory_session.commit()

        assert ok is True
        await inventory_session.refresh(inv)
        assert inv.locked_quantity == 25
        assert inv.version == 2

    async def test_release_caps_at_locked_amount(
        self, inventory_session, sample_inventory
    ):
        product, wh, inv = sample_inventory
        inv.locked_quantity = 10
        inv.version = 1
        await inventory_session.commit()

        repo = InventoryRepository(inventory_session)
        await repo.release(product.id, wh.id, 50)
        await inventory_session.commit()

        await inventory_session.refresh(inv)
        assert inv.locked_quantity == 0  # Capped, not negative


class TestInventoryRepositoryDeduct:
    async def test_deduct_decreases_both_quantity_and_locked(
        self, inventory_session, sample_inventory
    ):
        product, wh, inv = sample_inventory
        inv.locked_quantity = 30
        inv.version = 1
        await inventory_session.commit()

        repo = InventoryRepository(inventory_session)
        ok = await repo.deduct(product.id, wh.id, 20)
        await inventory_session.commit()

        assert ok is True
        await inventory_session.refresh(inv)
        assert inv.quantity == 80
        assert inv.locked_quantity == 10
        assert inv.version == 2

    async def test_deduct_raises_when_insufficient_physical(
        self, inventory_session, sample_inventory
    ):
        product, wh, inv = sample_inventory
        inv.quantity = 5
        await inventory_session.commit()

        repo = InventoryRepository(inventory_session)
        with pytest.raises(InsufficientStockError) as ei:
            await repo.deduct(product.id, wh.id, 10)
        assert ei.value.context["available"] == 5


class TestInventoryConcurrency:
    async def test_concurrent_reserve_prevents_oversell(self, engine, sample_inventory):
        """100 stock, 50 sequential requests for 30 each — at most 3 succeed.

        Note: SQLite serializes all writes, so we can't observe true races here.
        The optimistic-lock machinery is exercised by the sequential simulation
        and by the version-incrementing behavior. Production deployment uses
        PostgreSQL where this becomes a real concurrency test.
        """
        from sqlalchemy.ext.asyncio import async_sessionmaker

        product, wh, inv = sample_inventory
        session_factory = async_sessionmaker(engine, expire_on_commit=False)

        async def try_reserve():
            async with session_factory() as session:
                repo = InventoryRepository(session)
                try:
                    ok = await repo.reserve(product.id, wh.id, 30, max_retries=2)
                    await session.commit()
                    return ok
                except ConcurrentModificationError:
                    return False

        results = [await try_reserve() for _ in range(50)]
        successes = sum(1 for r in results if r)

        # Re-read final state in a fresh session
        async with session_factory() as session:
            from sqlalchemy import select

            refreshed = (
                await session.execute(select(Inventory).where(Inventory.id == inv.id))
            ).scalar_one()
            assert successes == 3, (
                f"expected 3 successful reservations, got {successes}"
            )
            assert refreshed.locked_quantity == 90
            assert refreshed.quantity == 100
            assert refreshed.locked_quantity <= 100
            assert refreshed.version == 3
