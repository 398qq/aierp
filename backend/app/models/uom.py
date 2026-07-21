"""Unit of Measure (UOM) and product packaging level models."""

import datetime
from decimal import Decimal

from sqlalchemy import (
    DECIMAL,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin


class UomDict(Base):
    """计量单位字典表 — 同时包含计数单位（PCS/PC/EA…）和包装单位（REEL/TUBE/TRAY…）。

    注意：用 code 作自然主键，不含自增 id。
    """

    __tablename__ = "uom_dict"

    code: Mapped[str] = mapped_column(String(20), primary_key=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    uom_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="count"
    )  # count / package
    category: Mapped[str | None] = mapped_column(String(30), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), nullable=True
    )
    deleted_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )

    pack_levels: Mapped[list["ProductPackLevel"]] = relationship(
        "ProductPackLevel",
        back_populates="uom",
        foreign_keys="ProductPackLevel.uom_code",
    )

    def __repr__(self) -> str:
        return f"<UomDict {self.code}: {self.name}>"


class ProductPackLevel(TimestampMixin, Base):
    """产品包装层级表 — 三层结构：基本单位(PCS) → 内包装(REEL) → 外包装(BOX)。

    每个产品最多 3 行（level 0/1/2），通过 qty_per_parent 建立换算关系。
    """

    __tablename__ = "product_pack_levels"

    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    uom_code: Mapped[str] = mapped_column(
        String(20), ForeignKey("uom_dict.code"), nullable=False
    )
    pack_level: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    qty_per_parent: Mapped[Decimal] = mapped_column(
        DECIMAL(18, 4), nullable=False, default=1
    )

    __table_args__ = (
        CheckConstraint("pack_level BETWEEN 0 AND 2", name="ck_pack_level_range"),
        Index(
            "idx_ppl_product_level",
            "product_id",
            "pack_level",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
            sqlite_where=text("deleted_at IS NULL"),
        ),
        Index(
            "idx_ppl_product",
            "product_id",
            postgresql_where=text("deleted_at IS NULL"),
            sqlite_where=text("deleted_at IS NULL"),
        ),
        Index(
            "idx_ppl_uom",
            "uom_code",
            postgresql_where=text("deleted_at IS NULL"),
            sqlite_where=text("deleted_at IS NULL"),
        ),
    )

    uom: Mapped["UomDict"] = relationship(
        "UomDict", back_populates="pack_levels", foreign_keys=[uom_code]
    )

    def __repr__(self) -> str:
        return f"<ProductPackLevel product={self.product_id} level={self.pack_level} uom={self.uom_code} qty={self.qty_per_parent}>"
