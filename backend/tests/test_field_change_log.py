"""Tests for field-level audit log (Stage 7)."""

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.audit import FieldChangeLog
from app.models.customer import Customer
from app.services.customer_service import CustomerService


# Use sqlite in-memory (avoid pgvector FK deps in this focused test)
@pytest_asyncio.fixture
async def db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        # Import models so Base knows about them
        from app.models.audit import FieldChangeLog  # noqa
        from app.models.customer import Customer  # noqa

        await conn.run_sync(Base.metadata.create_all)
    SessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with SessionLocal() as session:
        yield session
    await engine.dispose()


@pytest.mark.asyncio
async def test_update_with_audit_actor_records_field_change(db: AsyncSession):
    # Create customer
    cust = Customer(
        name="Acme", contact_person="Alice", email="old@acme.com", level="A"
    )
    db.add(cust)
    await db.commit()
    await db.refresh(cust)

    # Update with audit
    service = CustomerService()
    await service.update(db, cust, {"email": "new@acme.com"}, audit_actor="bob")

    # Verify field change log written
    from sqlalchemy import select

    logs = (
        (
            await db.execute(
                select(FieldChangeLog).where(FieldChangeLog.record_id == cust.id)
            )
        )
        .scalars()
        .all()
    )

    assert len(logs) == 1
    log = logs[0]
    assert log.table_name == "customers"
    assert log.field_name == "email"
    assert log.old_value == "old@acme.com"
    assert log.new_value == "new@acme.com"
    assert log.actor == "bob"


@pytest.mark.asyncio
async def test_update_without_audit_actor_writes_nothing(db: AsyncSession):
    cust = Customer(name="Acme", contact_person="Alice", email="a@x.com")
    db.add(cust)
    await db.commit()
    await db.refresh(cust)

    service = CustomerService()
    await service.update(db, cust, {"email": "b@x.com"})  # no audit_actor

    from sqlalchemy import select

    logs = (
        (
            await db.execute(
                select(FieldChangeLog).where(FieldChangeLog.record_id == cust.id)
            )
        )
        .scalars()
        .all()
    )
    assert len(logs) == 0


@pytest.mark.asyncio
async def test_noop_update_writes_nothing(db: AsyncSession):
    cust = Customer(name="Acme", contact_person="Alice", email="a@x.com")
    db.add(cust)
    await db.commit()
    await db.refresh(cust)

    service = CustomerService()
    await service.update(
        db, cust, {"email": "a@x.com"}, audit_actor="bob"
    )  # same value

    from sqlalchemy import select

    logs = (
        (
            await db.execute(
                select(FieldChangeLog).where(FieldChangeLog.record_id == cust.id)
            )
        )
        .scalars()
        .all()
    )
    assert len(logs) == 0


@pytest.mark.asyncio
async def test_multiple_field_changes_write_multiple_rows(db: AsyncSession):
    cust = Customer(name="Acme", contact_person="Alice", email="a@x.com", level="A")
    db.add(cust)
    await db.commit()
    await db.refresh(cust)

    service = CustomerService()
    await service.update(
        db,
        cust,
        {"email": "b@x.com", "level": "B", "contact_person": "Bob"},
        audit_actor="alice",
    )

    from sqlalchemy import select

    logs = (
        (
            await db.execute(
                select(FieldChangeLog)
                .where(FieldChangeLog.record_id == cust.id)
                .order_by(FieldChangeLog.field_name)
            )
        )
        .scalars()
        .all()
    )

    fields = {log.field_name for log in logs}
    assert fields == {"email", "level", "contact_person"}
    assert all(log.actor == "alice" for log in logs)


@pytest.mark.asyncio
async def test_none_value_skipped(db: AsyncSession):
    cust = Customer(name="Acme", contact_person="Alice", email="a@x.com")
    db.add(cust)
    await db.commit()
    await db.refresh(cust)

    service = CustomerService()
    await service.update(db, cust, {"email": None, "level": "B"}, audit_actor="bob")
    # Only "level" should be audited (None is PATCH skip)

    from sqlalchemy import select

    logs = (
        (
            await db.execute(
                select(FieldChangeLog).where(FieldChangeLog.record_id == cust.id)
            )
        )
        .scalars()
        .all()
    )

    assert len(logs) == 1
    assert logs[0].field_name == "level"
