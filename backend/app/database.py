from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.sql.elements import ColumnElement

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


def date_format(column, pg_fmt: str) -> ColumnElement:
    """Return a DB-agnostic date formatting expression.

    pg_fmt uses PostgreSQL to_char style (e.g. 'YYYY-MM', 'YYYYMM').
    Uses ORM-level adaptation so it works the same on SQLite and PostgreSQL.

    Strategy: cast date to text then extract the substring we need.
    'YYYY-MM' → chars 1-7, 'YYYYMM' → chars 1-4 + 6-7, 'YYYY' → chars 1-4.
    """
    from sqlalchemy import String, type_coerce

    date_str = type_coerce(column, String)
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
    await _ensure_pgvector(engine)
    await _seed_rbac(engine)
    await _seed_phase6(engine)


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
