from pgvector.sqlalchemy import Vector
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
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    supplier_id: Mapped[int | None] = mapped_column(ForeignKey("suppliers.id"), nullable=True)


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
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1024), nullable=True)


class Supplier(TimestampMixin, Base):
    __tablename__ = "suppliers"

    name: Mapped[str] = mapped_column(String(255))
    contact_person: Mapped[str | None] = mapped_column(String(100), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    product_lines: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    supplier_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    certifications: Mapped[str | None] = mapped_column(Text, nullable=True)
    payment_terms: Mapped[str | None] = mapped_column(String(100), nullable=True)
    region: Mapped[str | None] = mapped_column(String(50), nullable=True)
    website: Mapped[str | None] = mapped_column(String(255), nullable=True)
    financial_rating: Mapped[str | None] = mapped_column(String(10), nullable=True)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1024), nullable=True)


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


class InventoryTransaction(TimestampMixin, Base):
    __tablename__ = "inventory_transactions"

    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouses.id"))
    type: Mapped[str] = mapped_column(String(20))  # stock_in, stock_out, adjust, transfer
    quantity: Mapped[int] = mapped_column()
    before_qty: Mapped[int | None] = mapped_column(nullable=True)
    after_qty: Mapped[int | None] = mapped_column(nullable=True)
    reference_type: Mapped[str | None] = mapped_column(String(50), nullable=True)  # purchase, sales_order, manual
    reference_id: Mapped[int | None] = mapped_column(nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class SupplierProduct(TimestampMixin, Base):
    __tablename__ = "supplier_products"

    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.id"))
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    cost_price: Mapped[float | None] = mapped_column(DECIMAL(12, 4), nullable=True)
    lead_time_days: Mapped[int | None] = mapped_column(nullable=True)
    moq: Mapped[int | None] = mapped_column(nullable=True)  # minimum order quantity
    spq: Mapped[int | None] = mapped_column(nullable=True)  # standard package quantity
    is_preferred: Mapped[bool] = mapped_column(default=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
