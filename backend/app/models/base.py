import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import Mapped, mapped_column


class TimestampMixin:
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
    deleted_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, default=None)
