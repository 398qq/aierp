import os
import sys
from urllib.parse import urlparse

# Ensure backend/ is on the import path so 'from app ...' works
_BACKEND = os.path.join(os.path.dirname(__file__), "..")
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

# Tests must never inherit production authentication or cache targets.
os.environ["APP_ENV"] = "test"
os.environ["JWT_SECRET"] = "aierp-test-jwt-secret-2026-minimum-32-bytes-do-not-use-in-production"
os.environ["REDIS_URL"] = os.getenv(
    "TEST_REDIS_URL", "redis://localhost:6379/15"
)
test_database_url = os.getenv(
    "TEST_DATABASE_URL", "sqlite+aiosqlite:///:memory:"
)
if not test_database_url.startswith("sqlite") and os.getenv(
    "AIERP_ALLOW_EXTERNAL_TEST_DATABASE"
) != "1":
    raise RuntimeError(
        "Refusing external TEST_DATABASE_URL without "
        "AIERP_ALLOW_EXTERNAL_TEST_DATABASE=1"
    )
os.environ["TEST_DATABASE_URL"] = test_database_url
os.environ["DB_URL_OVERRIDE"] = test_database_url

import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
import sqlalchemy as sa  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy import select  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine  # noqa: E402

from app.core.security import create_access_token, hash_password  # noqa: E402
from app.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402

TEST_DATABASE_URL = os.environ["TEST_DATABASE_URL"]


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


@pytest_asyncio.fixture(scope="function")
async def engine():
    ext = {}
    if "sqlite" in TEST_DATABASE_URL:
        ext["connect_args"] = {"check_same_thread": False}
    else:
        # PostgreSQL: single connection to avoid "another operation in progress" errors
        ext["pool_size"] = 1
        ext["max_overflow"] = 0
    test_engine = create_async_engine(TEST_DATABASE_URL, echo=False, **ext)
    yield test_engine
    await test_engine.dispose()


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
    session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
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
    from app.models.rbac import (
        Permission,
        Role,
        role_permissions_table,
        user_roles_table,
    )
    from app.models.user import User

    password = "testpass123"
    user = User(username="testuser", password=hash_password(password), role="sales")
    db_session.add(user)
    await db_session.flush()
    role = (
        await db_session.execute(select(Role).where(Role.name == "sales"))
    ).scalar_one_or_none()
    if role is None:
        role = Role(name="sales", description="销售")
        db_session.add(role)
        await db_session.flush()
    permissions = (
        (
            await db_session.execute(
                select(Permission).where(
                    Permission.resource == "customers",
                    Permission.action.in_(["read", "write", "delete", "export"]),
                )
            )
        )
        .scalars()
        .all()
    )
    existing_actions = {permission.action for permission in permissions}
    for action in ("read", "write", "delete", "export"):
        if action not in existing_actions:
            permission = Permission(
                resource="customers",
                action=action,
                name=f"测试客户权限:{action}",
            )
            db_session.add(permission)
            permissions.append(permission)
    await db_session.flush()
    await db_session.execute(
        user_roles_table.insert().values(user_id=user.id, role_id=role.id)
    )
    for permission in permissions:
        existing_link = await db_session.scalar(
            select(role_permissions_table.c.role_id).where(
                role_permissions_table.c.role_id == role.id,
                role_permissions_table.c.permission_id == permission.id,
            )
        )
        if existing_link is None:
            await db_session.execute(
                role_permissions_table.insert().values(
                    role_id=role.id,
                    permission_id=permission.id,
                )
            )
    from app.services.cache_service import cache_delete

    for action in ("read", "write", "delete", "export"):
        await cache_delete(f"perm:{user.id}:customers:{action}")
    token = create_access_token(user.id, user.username)
    return {
        "id": user.id,
        "username": user.username,
        "password": password,
        "token": token,
    }


@pytest_asyncio.fixture
async def auth_headers(test_user):
    return {"Authorization": f"Bearer {test_user['token']}"}


@pytest_asyncio.fixture
async def test_admin(db_session) -> dict:
    from app.models.user import User
    from app.models.rbac import Role

    password = "admin123"
    admin = User(username="adminuser", password=hash_password(password), role="admin")
    db_session.add(admin)
    await db_session.flush()

    # Ensure admin RBAC role exists and is assigned for permission checks
    result = await db_session.execute(select(Role).where(Role.name == "admin"))
    admin_role = result.scalar_one_or_none()
    if admin_role is None:
        admin_role = Role(name="admin", description="系统管理员")
        db_session.add(admin_role)
        await db_session.flush()
    # Insert association directly to avoid lazy="selectin" triggering async IO
    # under aiosqlite, which would fail with MissingGreenlet
    from app.models.rbac import user_roles_table

    await db_session.execute(
        user_roles_table.insert().values(user_id=admin.id, role_id=admin_role.id)
    )
    await db_session.flush()

    token = create_access_token(admin.id, admin.username)
    return {
        "id": admin.id,
        "username": admin.username,
        "password": password,
        "token": token,
    }


@pytest_asyncio.fixture
async def admin_headers(test_admin):
    return {"Authorization": f"Bearer {test_admin['token']}"}


# ── Stage 10 Day 1: clean TELEGRAM_* env between tests ────────────


@pytest_asyncio.fixture(autouse=True)
async def _clean_redis_cache():
    """Clear only the dedicated test Redis database between tests.

    Root cause: require_perm() caches perm:{user_id}:{resource}:{action} in
    Redis (PERM_CACHE_TTL). test_user and test_admin in the same process can
    share the cache, so a previous admin's allow leaks into a sales user's
    permission check. The test suite is pinned to Redis DB 15 so cleanup cannot
    delete runtime sessions, permissions, or business caches from DB 0.
    """
    redis_url = os.environ["REDIS_URL"]
    redis_db = urlparse(redis_url).path.lstrip("/")
    if os.environ.get("APP_ENV") != "test" or redis_db in {"", "0"}:
        raise RuntimeError("Refusing to clean Redis outside the dedicated test DB")

    async def _flush() -> None:
        try:
            from app.services.cache_service import get_redis

            r = await get_redis()
            if r is not None:
                keys = []
                async for k in r.scan_iter(match="aierp:*"):
                    keys.append(k)
                if keys:
                    await r.delete(*keys)
        except Exception:
            pass

    await _flush()
    yield
    await _flush()
    from app.database import engine as app_engine
    from app.services.cache_service import close_redis

    await close_redis()
    await app_engine.dispose()


@pytest.fixture(autouse=True)
def _clean_telegram_env():
    """Reset Telegram env vars before each test.

    Stage 10 Day 1: test_telegram_notifier's patch.dict + os.environ.pop
    can leak into subsequent tests. Reset to a clean slate.
    """
    saved = {
        "TELEGRAM_BOT_TOKEN": os.environ.pop("TELEGRAM_BOT_TOKEN", None),
        "TELEGRAM_CHAT_ID": os.environ.pop("TELEGRAM_CHAT_ID", None),
        "TELEGRAM_DISABLED": os.environ.pop("TELEGRAM_DISABLED", None),
    }
    yield
    for k, v in saved.items():
        if v is not None:
            os.environ[k] = v
        else:
            os.environ.pop(k, None)
