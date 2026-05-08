import os
import sys

# Ensure backend/ is on the import path so 'from app ...' works
_BACKEND = os.path.join(os.path.dirname(__file__), "..")
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

import pytest
import pytest_asyncio
import sqlalchemy as sa
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.security import create_access_token, hash_password
from app.database import Base, get_db
from app.main import app

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "sqlite+aiosqlite:///./test.db",
)


def _patch_vector_columns():
    """Replace pgvector Vector columns with Text for SQLite compatibility."""
    try:
        from pgvector.sqlalchemy import Vector
    except ImportError:
        Vector = None

    for table in Base.metadata.sorted_tables:
        for col in list(table.columns):
            if Vector is not None and isinstance(col.type, Vector):
                col.type = sa.Text()


@pytest.fixture(scope="session")
def engine():
    ext = {}
    if "sqlite" in TEST_DATABASE_URL:
        ext["connect_args"] = {"check_same_thread": False}
    else:
        # PostgreSQL: single connection to avoid "another operation in progress" errors
        ext["pool_size"] = 1
        ext["max_overflow"] = 0
    return create_async_engine(TEST_DATABASE_URL, echo=False, **ext)


@pytest_asyncio.fixture(scope="function")
async def create_tables(engine):
    _patch_vector_columns()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def db_session(engine, create_tables):
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def async_client(db_session):
    async def override_get_db():
        try:
            yield db_session
            await db_session.commit()
        except Exception:
            await db_session.rollback()
            raise

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def test_customer(db_session) -> dict:
    from app.models.customer import Customer

    customer = Customer(name="测试客户", industry="电子", level="A")
    db_session.add(customer)
    await db_session.flush()
    return {"id": customer.id, "name": customer.name}


@pytest_asyncio.fixture
async def test_user(db_session) -> dict:
    from app.models.user import User

    password = "testpass123"
    user = User(username="testuser", password=hash_password(password), role="sales")
    db_session.add(user)
    await db_session.flush()
    token = create_access_token(user.id, user.username)
    return {"id": user.id, "username": user.username, "password": password, "token": token}


@pytest_asyncio.fixture
async def auth_headers(test_user):
    return {"Authorization": f"Bearer {test_user['token']}"}
