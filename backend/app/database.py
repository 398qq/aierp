from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=settings.DEBUG, pool_size=20, max_overflow=10)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # Run pgvector migration if needed
    await _ensure_pgvector(engine)
    # Seed RBAC data if empty
    await _seed_rbac(engine)


async def _ensure_pgvector(eng):
    """Ensure pgvector extension and column type are set up. Skips gracefully if no permission."""
    import pathlib

    async with eng.connect() as conn:
        try:
            await conn.exec_driver_sql("CREATE EXTENSION IF NOT EXISTS vector")
        except Exception:
            pass  # Extension may already exist or user lacks privilege

        # Check if embedding column needs migration from JSON to VECTOR
        try:
            result = await conn.exec_driver_sql(
                "SELECT data_type FROM information_schema.columns "
                "WHERE table_name = 'customers' AND column_name = 'embedding'"
            )
            row = result.fetchone()
        except Exception:
            row = None

        if row and row[0] in ('json', 'jsonb'):
            migration_path = pathlib.Path(__file__).resolve().parent / "migrations" / "001_pgvector_embedding.sql"
            if migration_path.exists():
                sql = migration_path.read_text()
                for stmt in sql.split(";"):
                    stmt = stmt.strip()
                    if stmt and not stmt.startswith("--") and "CREATE EXTENSION" not in stmt.upper():
                        try:
                            await conn.exec_driver_sql(stmt + ";")
                        except Exception:
                            pass

        # Ensure IVFFlat indexes exist for products and suppliers
        for idx_file in ("003_product_embedding_index.sql", "004_supplier_embedding_index.sql"):
            idx_path = pathlib.Path(__file__).resolve().parent / "migrations" / idx_file
            if idx_path.exists():
                try:
                    await conn.exec_driver_sql(idx_path.read_text().split(";")[0].strip() + ";")
                except Exception:
                    pass
        await conn.commit()


async def _seed_rbac(eng):
    """Seed default RBAC data (permissions, roles, assignments) if tables are empty."""
    async with eng.connect() as conn:
        from sqlalchemy import text

        # Check if permissions already exist
        result = await conn.exec_driver_sql("SELECT count(*) FROM permissions WHERE deleted_at IS NULL")
        row = result.fetchone()
        if row and row[0] > 0:
            return  # Already seeded

        import pathlib
        seed_path = pathlib.Path(__file__).resolve().parent / "migrations" / "005-phase5-rbac.sql"
        if seed_path.exists():
            sql = seed_path.read_text()
            # Skip CREATE TABLE / ALTER TABLE — already done by create_all
            for stmt in sql.split(";"):
                stmt = stmt.strip()
                if not stmt or stmt.startswith("--"):
                    continue
                upper = stmt.upper()
                if "CREATE TABLE" in upper or "ALTER TABLE" in upper:
                    continue
                try:
                    await conn.exec_driver_sql(stmt + ";")
                except Exception:
                    pass
        await conn.commit()
