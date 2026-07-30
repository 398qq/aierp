"""User preferences: per-(user, scope, key) JSON value store.

Used for client-side preferences that should sync across devices:
- scope='products' key='column_visibility' value={...}
- scope='products' key='saved_views' value=[{...}, ...]

Backed by a partial unique index (user_id, scope, key) — same shape
as a dictionary keyed by (scope, key) per user.
"""
from sqlalchemy import ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TimestampMixin


class UserPreference(TimestampMixin, Base):
    __tablename__ = "user_preferences"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    scope: Mapped[str] = mapped_column(String(64), nullable=False)
    key: Mapped[str] = mapped_column(String(64), nullable=False)
    # value is JSON-serialized text; frontend (and any caller) parses it.
    # Text instead of JSONB to keep SQLite + PostgreSQL parity in tests.
    value: Mapped[str] = mapped_column(Text, nullable=False, default="null")

    __table_args__ = (
        UniqueConstraint("user_id", "scope", "key", name="uq_user_pref_lookup"),
        Index("ix_user_pref_scope_key", "scope", "key"),
    )
