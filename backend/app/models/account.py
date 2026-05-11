from sqlalchemy import DECIMAL, Boolean, Date, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin


class Account(TimestampMixin, Base):
    __tablename__ = "accounts"

    code: Mapped[str] = mapped_column(String(30), unique=True)
    name: Mapped[str] = mapped_column(String(100))
    type: Mapped[str] = mapped_column(String(20))  # asset/liability/equity/income/expense
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("accounts.id"), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    parent = relationship("Account", remote_side="Account.id", backref="children")


class JournalEntry(TimestampMixin, Base):
    __tablename__ = "journal_entries"

    entry_no: Mapped[str] = mapped_column(String(50))
    entry_date: Mapped[Date] = mapped_column(Date)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="draft")  # draft/posted/reversed
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    posted_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    posted_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    lines = relationship("JournalEntryLine", back_populates="entry", lazy="selectin")
    creator = relationship("User", foreign_keys=[created_by])
    poster = relationship("User", foreign_keys=[posted_by])


class JournalEntryLine(TimestampMixin, Base):
    __tablename__ = "journal_entry_lines"

    entry_id: Mapped[int] = mapped_column(ForeignKey("journal_entries.id"))
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    debit: Mapped[float] = mapped_column(DECIMAL(15, 2), default=0)
    credit: Mapped[float] = mapped_column(DECIMAL(15, 2), default=0)

    entry = relationship("JournalEntry", back_populates="lines")
    account = relationship("Account")


class BankReconciliation(TimestampMixin, Base):
    __tablename__ = "bank_reconciliations"

    payment_id: Mapped[int | None] = mapped_column(ForeignKey("payment_records.id"), nullable=True)
    bank_txn_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    bank_date: Mapped[Date | None] = mapped_column(Date, nullable=True)
    bank_amount: Mapped[float | None] = mapped_column(DECIMAL(15, 2), nullable=True)
    bank_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    match_type: Mapped[str] = mapped_column(String(20), default="auto")  # auto/manual/unmatched
    difference: Mapped[float] = mapped_column(DECIMAL(15, 2), default=0)
    reconciled_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    reconciled_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    payment = relationship("PaymentRecord", foreign_keys=[payment_id])
    reconciler = relationship("User", foreign_keys=[reconciled_by])


class NotificationTemplate(TimestampMixin, Base):
    __tablename__ = "notification_templates"

    code: Mapped[str] = mapped_column(String(50), unique=True)
    name: Mapped[str] = mapped_column(String(100))
    channel: Mapped[str] = mapped_column(String(30), default="in_app")  # in_app/email/wecom_webhook
    event_type: Mapped[str] = mapped_column(String(50))
    subject_template: Mapped[str | None] = mapped_column(String(255), nullable=True)
    body_template: Mapped[str] = mapped_column(Text)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)


class NotificationPreference(TimestampMixin, Base):
    __tablename__ = "notification_preferences"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    event_type: Mapped[str] = mapped_column(String(50))
    channel: Mapped[str] = mapped_column(String(30), default="in_app")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)


class IntegrationConfig(TimestampMixin, Base):
    __tablename__ = "integration_configs"

    type: Mapped[str] = mapped_column(String(30))  # ecommerce/logistics/webhook/email
    name: Mapped[str] = mapped_column(String(100))
    api_key_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    api_secret_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    endpoint: Mapped[str | None] = mapped_column(String(500), nullable=True)
    settings: Mapped[dict | None] = mapped_column(JSON, default=dict)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
