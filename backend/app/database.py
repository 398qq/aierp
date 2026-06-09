import json
import logging
import time

from sqlalchemy import func
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.sql.elements import ColumnElement

from app.config import settings
from app.core.request_context import get_request_id

slow_query_logger = logging.getLogger("app.db.slow_query")

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_recycle=settings.DB_POOL_RECYCLE_SECONDS,
    pool_pre_ping=settings.DB_POOL_PRE_PING,
)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


def _normalize_sql(statement: str, max_length: int = 400) -> str:
    normalized = " ".join(statement.split())
    if len(normalized) > max_length:
        return normalized[:max_length] + "..."
    return normalized


def _install_slow_query_logging(target_engine=None) -> None:
    async_engine = target_engine or engine
    sync_engine = async_engine.sync_engine
    if getattr(sync_engine, "_aierp_slow_query_listener_installed", False):
        return
    setattr(sync_engine, "_aierp_slow_query_listener_installed", True)

    @event.listens_for(sync_engine, "before_cursor_execute")
    def _before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        conn.info.setdefault("query_start_time", []).append(time.perf_counter())

    @event.listens_for(sync_engine, "after_cursor_execute")
    def _after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        timings = conn.info.get("query_start_time")
        if not timings:
            return
        started = timings.pop(-1)
        elapsed_ms = (time.perf_counter() - started) * 1000
        if elapsed_ms < settings.SLOW_QUERY_THRESHOLD_MS:
            return

        payload = {
            "event": "slow_query",
            "request_id": get_request_id() or None,
            "duration_ms": round(elapsed_ms, 2),
            "threshold_ms": settings.SLOW_QUERY_THRESHOLD_MS,
            "sql": _normalize_sql(statement),
        }
        slow_query_logger.warning(json.dumps(payload, ensure_ascii=False))


_install_slow_query_logging()


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


def date_format(column, pg_fmt: str) -> ColumnElement:
    """Return a DB-agnostic date formatting expression.

    pg_fmt uses PostgreSQL to_char style (e.g. 'YYYY-MM', 'YYYYMM').
    Uses ORM-level adaptation so it works the same on SQLite and PostgreSQL.

    Strategy: cast date/timestamp to text then extract the substring we need.
    'YYYY-MM' → chars 1-7, 'YYYYMM' → chars 1-4 + 6-7, 'YYYY' → chars 1-4.

    Note: must use ``func.cast(col, String)`` (not ``type_coerce``) so that
    PostgreSQL generates an explicit ``::text`` / ``CAST(... AS VARCHAR)``
    cast. Without it, ``substr`` receives a raw ``date`` / ``timestamp``
    column and raises ``UndefinedFunctionError`` because PostgreSQL has no
    3-argument ``substr`` overload for those types.
    """
    from sqlalchemy import String

    date_str = func.cast(column, String)
    if pg_fmt == "YYYY-MM":
        return func.substr(date_str, 1, 7)
    if pg_fmt == "YYYYMM":
        return func.substr(date_str, 1, 4) + func.substr(date_str, 6, 2)
    if pg_fmt == "YYYY":
        return func.substr(date_str, 1, 4)
    return date_str


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await _ensure_brand_schema(engine)
    await _ensure_phase6_schema(engine)
    await _ensure_payment_delivery_note_schema(engine)
    await _ensure_quotation_item_cost_schema(engine)
    await _ensure_critical_indexes(engine)
    await _ensure_pgvector(engine)
    await _ensure_customer_status_machine(engine)
    await _seed_rbac(engine)
    await _seed_phase6(engine)


async def _ensure_customer_status_machine(eng) -> None:
    """Apply the customer status machine migration (020-customer-status-machine.sql)."""
    import logging
    import pathlib
    _log = logging.getLogger("app.db.migration")
    if eng.dialect.name != "postgresql":
        return
    sql_path = pathlib.Path(__file__).resolve().parent / "migrations" / "020-customer-status-machine.sql"
    if not sql_path.exists():
        return
    sql = sql_path.read_text()
    async with eng.begin() as conn:
        for stmt in sql.split(";"):
            stmt = stmt.strip()
            if not stmt or stmt.startswith("--"):
                continue
            try:
                await conn.exec_driver_sql(stmt + ";")
            except Exception as exc:  # noqa: BLE001
                _log.warning("Customer status migration failed (non-fatal): %s", exc)


async def _ensure_critical_indexes(eng) -> None:
    """Apply critical performance indexes on hot-path query columns.

    The SQL file `migrations/008_critical_indexes.sql` is idempotent
    (uses `CREATE INDEX IF NOT EXISTS`) and runs on every startup so
    the deployment is self-healing. SQLite is skipped (it has no
    partial-index support needed for the WHERE-clause filtering).
    """
    import logging
    import pathlib
    _log = logging.getLogger("app.db.migration")
    if eng.dialect.name != "postgresql":
        return
    sql_path = pathlib.Path(__file__).resolve().parent / "migrations" / "008_critical_indexes.sql"
    if not sql_path.exists():
        return
    sql = sql_path.read_text()
    async with eng.begin() as conn:
        for stmt in sql.split(";"):
            stmt = stmt.strip()
            if not stmt or stmt.startswith("--"):
                continue
            try:
                await conn.exec_driver_sql(stmt + ";")
            except Exception as exc:  # noqa: BLE001
                _log.warning("Index migration failed (non-fatal): %s", exc)


async def _ensure_brand_schema(eng):
    """Backfill columns that create_all will not add to existing tables."""
    if eng.dialect.name != "postgresql":
        return

    async with eng.connect() as conn:
        for table in ("brands", "suppliers", "warehouses", "inventories", "supplier_products"):
            for column in ("created_by", "updated_by"):
                await conn.exec_driver_sql(
                    f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} BIGINT REFERENCES users(id)"
                )
        await conn.exec_driver_sql(
            "ALTER TABLE inventories ADD COLUMN IF NOT EXISTS version INT NOT NULL DEFAULT 0"
        )
        await conn.commit()


async def _ensure_phase6_schema(eng):
    """Backfill Phase 6 columns that may be missing in long-lived local DBs."""
    if eng.dialect.name != "postgresql":
        return

    async with eng.connect() as conn:
        await conn.exec_driver_sql("ALTER TABLE notifications ADD COLUMN IF NOT EXISTS channel VARCHAR(30) DEFAULT 'in_app'")
        await conn.exec_driver_sql("ALTER TABLE notifications ADD COLUMN IF NOT EXISTS template_code VARCHAR(50)")
        await conn.exec_driver_sql("ALTER TABLE notifications ADD COLUMN IF NOT EXISTS external_id VARCHAR(100)")
        await conn.commit()


async def _ensure_quotation_item_cost_schema(eng):
    """Backfill quotation item cost columns for long-lived local databases."""
    if eng.dialect.name != "postgresql":
        return

    async with eng.connect() as conn:
        await conn.exec_driver_sql("ALTER TABLE quotation_items ADD COLUMN IF NOT EXISTS cost_price DECIMAL(20,6)")
        await conn.exec_driver_sql("ALTER TABLE quotation_items ADD COLUMN IF NOT EXISTS untaxed_cost DECIMAL(20,6)")
        await conn.exec_driver_sql("ALTER TABLE quotation_items ADD COLUMN IF NOT EXISTS taxed_cost DECIMAL(20,6)")
        await conn.exec_driver_sql("ALTER TABLE quotation_items ADD COLUMN IF NOT EXISTS sales_profit DECIMAL(20,6)")
        await conn.commit()


async def _ensure_payment_delivery_note_schema(eng):
    """Backfill delivery_note_id column on payment_records for existing databases."""
    if eng.dialect.name != "postgresql":
        return

    async with eng.connect() as conn:
        await conn.exec_driver_sql("ALTER TABLE payment_records ADD COLUMN IF NOT EXISTS delivery_note_id BIGINT REFERENCES delivery_notes(id)")
        await conn.exec_driver_sql("CREATE INDEX IF NOT EXISTS idx_payment_records_delivery_note_id ON payment_records(delivery_note_id)")
        await conn.commit()


async def _ensure_pgvector(eng):
    """Ensure pgvector extension and column type are set up."""
    import pathlib

    async with eng.connect() as conn:
        try:
            await conn.exec_driver_sql("CREATE EXTENSION IF NOT EXISTS vector")
        except Exception:
            pass

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

        for idx_file in ("003_product_embedding_index.sql", "004_supplier_embedding_index.sql"):
            idx_path = pathlib.Path(__file__).resolve().parent / "migrations" / idx_file
            if idx_path.exists():
                try:
                    await conn.exec_driver_sql(idx_path.read_text().split(";")[0].strip() + ";")
                except Exception:
                    pass
        await conn.commit()


async def _seed_rbac(eng):
    """Seed default RBAC data if tables are empty."""
    async with eng.connect() as conn:
        result = await conn.exec_driver_sql("SELECT count(*) FROM permissions WHERE deleted_at IS NULL")
        row = result.fetchone()
        if row and row[0] > 0:
            return

        import pathlib
        seed_path = pathlib.Path(__file__).resolve().parent / "migrations" / "005-phase5-rbac.sql"
        if seed_path.exists():
            sql = seed_path.read_text()
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


async def _seed_phase6(eng):
    """Seed Phase 6 data (accounts, notification templates) using ORM."""
    from sqlalchemy import select

    async with eng.connect() as conn:
        from sqlalchemy import text
        result = await conn.execute(text("SELECT count(*) FROM accounts WHERE deleted_at IS NULL"))
        row = result.fetchone()
        if row and row[0] > 0:
            return

    # Use ORM session for seeding
    from app.models.account import Account, NotificationTemplate

    async with async_session() as session:
        # Seed accounts
        acct_data = [
            ("1001", "库存现金", "asset", "现金"),
            ("1002", "银行存款", "asset", "银行存款"),
            ("1122", "应收账款", "asset", "应收客户货款"),
            ("1403", "库存商品", "asset", "库存商品"),
            ("2001", "短期借款", "liability", "短期借款"),
            ("2202", "应付账款", "liability", "应付供应商货款"),
            ("2221", "应交税费", "liability", "应交税费"),
            ("3001", "实收资本", "equity", "实收资本"),
            ("3101", "未分配利润", "equity", "未分配利润"),
            ("4001", "主营业务收入", "income", "销售收入"),
            ("4002", "其他业务收入", "income", "其他收入"),
            ("5001", "主营业务成本", "expense", "销售成本"),
            ("5002", "管理费用", "expense", "管理费用"),
            ("5003", "销售费用", "expense", "销售费用"),
            ("5004", "财务费用", "expense", "财务费用"),
        ]
        for code, name, atype, desc in acct_data:
            existing = (await session.execute(
                select(Account).where(Account.code == code, Account.deleted_at.is_(None))
            )).scalars().first()
            if not existing:
                session.add(Account(code=code, name=name, type=atype, description=desc))

        # Seed notification templates
        tmpl_data = [
            ("approval_request", "审批请求", "in_app", "approval_requested",
             "新的审批请求: {{doc_type}} #{{doc_id}}",
             "{{submitter}} 提交了 {{doc_type}} #{{doc_id}} 的审批请求，金额 ¥{{amount}}，请审批。"),
            ("approval_result", "审批结果", "in_app", "approval_completed",
             "审批结果: {{doc_type}} #{{doc_id}}",
             "您的 {{doc_type}} #{{doc_id}} 审批{{result}}。{{comment}}"),
            ("daily_report", "日报摘要", "in_app", "daily_report",
             "AIERP 经营日报 — {{report_date}}",
             "今日销售: ¥{{revenue}} | 新客户: {{new_customers}} | 回款: ¥{{payments}} | 库存预警: {{stock_alerts}}"),
            ("stock_alert", "库存预警", "in_app", "stock_low",
             "库存预警: {{product_name}}",
             "产品 {{product_name}} ({{sku}}) 库存 {{current_qty}} 低于安全库存 {{safety_stock}}"),
        ]
        for code, name, channel, event, subject, body in tmpl_data:
            existing = (await session.execute(
                select(NotificationTemplate).where(NotificationTemplate.code == code, NotificationTemplate.deleted_at.is_(None))
            )).scalars().first()
            if not existing:
                session.add(NotificationTemplate(
                    code=code, name=name, channel=channel, event_type=event,
                    subject_template=subject, body_template=body,
                ))

        await session.commit()
