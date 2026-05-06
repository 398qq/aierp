from sqlalchemy import DECIMAL, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TimestampMixin


class Brand(TimestampMixin, Base):
    __tablename__ = "brands"

    name: Mapped[str] = mapped_column(String(255))
    name_cn: Mapped[str | None] = mapped_column(String(255), nullable=True)
    website: Mapped[str | None] = mapped_column(String(500), nullable=True)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class Product(TimestampMixin, Base):
    __tablename__ = "products"

    sku: Mapped[str | None] = mapped_column(String(100), nullable=True)
    name: Mapped[str] = mapped_column(String(255))
    brand_id: Mapped[int | None] = mapped_column(ForeignKey("brands.id"), nullable=True)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    package_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    specs: Mapped[str | None] = mapped_column(Text, nullable=True)
    unit: Mapped[str | None] = mapped_column(String(20), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)


class Supplier(TimestampMixin, Base):
    __tablename__ = "suppliers"

    name: Mapped[str] = mapped_column(String(255))
    contact_person: Mapped[str | None] = mapped_column(String(100), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    product_lines: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class Warehouse(TimestampMixin, Base):
    __tablename__ = "warehouses"

    name: Mapped[str] = mapped_column(String(100))
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)


class Inventory(TimestampMixin, Base):
    __tablename__ = "inventories"

    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouses.id"))
    quantity: Mapped[int] = mapped_column(default=0)
    safety_stock: Mapped[int] = mapped_column(default=0)
