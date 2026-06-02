from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean, CheckConstraint, DateTime, DECIMAL, Float, ForeignKey, Integer, String, Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin

import datetime


class Brand(TimestampMixin, Base):
    __tablename__ = "brands"

    # --- 基础参数 ---
    code: Mapped[str | None] = mapped_column(String(50), nullable=True, unique=True)
    name: Mapped[str] = mapped_column(String(255))
    name_cn: Mapped[str | None] = mapped_column(String(255), nullable=True)
    short_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    logo: Mapped[str | None] = mapped_column(String(500), nullable=True)
    brand_type: Mapped[str | None] = mapped_column(String(50), nullable=True)  # own_brand / agency / oem
    status: Mapped[str] = mapped_column(String(20), default="active")  # active / inactive / frozen
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # --- 商业参数 ---
    level: Mapped[str | None] = mapped_column(String(10), nullable=True)  # A / B / C
    positioning: Mapped[str | None] = mapped_column(String(50), nullable=True)  # high / mid / low
    owner: Mapped[str | None] = mapped_column(String(100), nullable=True)
    product_lines: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_markets: Mapped[str | None] = mapped_column(Text, nullable=True)
    website: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # --- 供应链参数 ---
    supplier_id: Mapped[int | None] = mapped_column(ForeignKey("suppliers.id"), nullable=True)
    manufacturer_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    authorization_status: Mapped[str | None] = mapped_column(String(50), nullable=True)  # authorized / unauthorized / unknown
    lifecycle_stage: Mapped[str | None] = mapped_column(String(50), nullable=True)  # active / nrnd / eol
    is_automotive: Mapped[bool] = mapped_column(Boolean, default=False)
    moq: Mapped[int | None] = mapped_column(Integer, nullable=True)
    lead_time_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    risk_level: Mapped[str | None] = mapped_column(String(50), nullable=True)  # low / medium / high / critical
    rohs_status: Mapped[str | None] = mapped_column(String(50), nullable=True)  # compliant / non_compliant / exempt / unknown

    # --- AI 参数 ---
    ai_keywords: Mapped[str | None] = mapped_column(Text, nullable=True)
    risk_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    alternative_brands: Mapped[str | None] = mapped_column(Text, nullable=True)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1024), nullable=True)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    updated_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    supplier = relationship("Supplier", foreign_keys=[supplier_id])
    products = relationship("Product", back_populates="brand", lazy="selectin")


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

    brand = relationship("Brand", back_populates="products", lazy="selectin")
    quotation_items = relationship("QuotationItem", back_populates="product", lazy="selectin")
    sales_order_items = relationship("SalesOrderItem", back_populates="product", lazy="selectin")
    delivery_note_items = relationship("DeliveryNoteItem", back_populates="product", lazy="selectin")


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
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    updated_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    supplier_products = relationship("SupplierProduct", foreign_keys="SupplierProduct.supplier_id", lazy="selectin")


class Warehouse(TimestampMixin, Base):
    __tablename__ = "warehouses"

    name: Mapped[str] = mapped_column(String(100))
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    updated_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)


class Inventory(TimestampMixin, Base):
    __tablename__ = "inventories"

    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouses.id"))
    quantity: Mapped[int] = mapped_column(default=0)
    safety_stock: Mapped[int] = mapped_column(default=0)
    locked_quantity: Mapped[int] = mapped_column(default=0)
    unit_price: Mapped[float | None] = mapped_column(DECIMAL(20, 6), nullable=True, default=None)
    version: Mapped[int] = mapped_column(default=0, nullable=False)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    updated_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)


class InventoryBatchORM(TimestampMixin, Base):
    """One row per receipt batch — traceability for ROHS / MSL / perishable items.

    Each batch has its own quantity, cost, expiry. The application
    layer uses FEFO allocation to pick which batch to deduct from.
    """

    __tablename__ = "inventory_batches"
    __table_args__ = (
        UniqueConstraint("product_id", "warehouse_id", "batch_no", name="uq_inv_batch_pkey"),
        CheckConstraint("quantity >= 0", name="ck_inv_batch_qty_nonneg"),
    )

    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouses.id"))
    batch_no: Mapped[str] = mapped_column(String(50), nullable=False)
    quantity: Mapped[int] = mapped_column(default=0, nullable=False)
    locked_quantity: Mapped[int] = mapped_column(default=0, nullable=False)
    unit_cost: Mapped[float] = mapped_column(DECIMAL(20, 6), default=0)
    received_date: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), default=datetime.datetime.utcnow
    )
    expiry_date: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    manufacture_date: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    supplier_id: Mapped[int | None] = mapped_column(ForeignKey("suppliers.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="available")
    rohs_compliant: Mapped[bool] = mapped_column(Boolean, default=True)
    msl_level: Mapped[str | None] = mapped_column(String(5), nullable=True)
    certificate_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    product = relationship("Product", foreign_keys=[product_id])
    warehouse = relationship("Warehouse", foreign_keys=[warehouse_id])
    supplier = relationship("Supplier", foreign_keys=[supplier_id])


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
    cost_price: Mapped[float | None] = mapped_column(DECIMAL(20, 6), nullable=True)
    lead_time_days: Mapped[int | None] = mapped_column(nullable=True)
    moq: Mapped[int | None] = mapped_column(nullable=True)  # minimum order quantity
    spq: Mapped[int | None] = mapped_column(nullable=True)  # standard package quantity
    is_preferred: Mapped[bool] = mapped_column(default=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    updated_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
