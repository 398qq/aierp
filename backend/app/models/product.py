from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    DECIMAL,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
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
    brand_type: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )  # own_brand / agency / oem
    status: Mapped[str] = mapped_column(
        String(20), default="active"
    )  # active / inactive / frozen
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # --- 商业参数 ---
    level: Mapped[str | None] = mapped_column(String(10), nullable=True)  # A / B / C
    positioning: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )  # high / mid / low
    owner: Mapped[str | None] = mapped_column(String(100), nullable=True)
    product_lines: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_markets: Mapped[str | None] = mapped_column(Text, nullable=True)
    website: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # --- 供应链参数 ---
    supplier_id: Mapped[int | None] = mapped_column(
        ForeignKey("suppliers.id"), nullable=True
    )
    manufacturer_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    authorization_status: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )  # authorized / unauthorized / unknown
    lifecycle_stage: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )  # active / nrnd / eol
    is_automotive: Mapped[bool] = mapped_column(Boolean, default=False)
    moq: Mapped[int | None] = mapped_column(Integer, nullable=True)
    lead_time_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    risk_level: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )  # low / medium / high / critical
    rohs_status: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )  # compliant / non_compliant / exempt / unknown

    # --- AI 参数 ---
    ai_keywords: Mapped[str | None] = mapped_column(Text, nullable=True)
    risk_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    alternative_brands: Mapped[str | None] = mapped_column(Text, nullable=True)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1536), nullable=True)
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    updated_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )

    supplier = relationship("Supplier", foreign_keys=[supplier_id])
    products = relationship("Product", back_populates="brand", lazy="selectin")


class Product(TimestampMixin, Base):
    __tablename__ = "products"

    # ── 基础标识 ──
    sku: Mapped[str | None] = mapped_column(String(100), nullable=True)
    name: Mapped[str] = mapped_column(String(255))
    mpn: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )  # Manufacturer Part Number
    datecode: Mapped[str | None] = mapped_column(String(100), nullable=True)
    barcode: Mapped[str | None] = mapped_column(String(50), nullable=True)  # UPC / EAN
    hs_code: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )  # HS 海关编码
    origin_country: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )  # 原产国

    # ── 归属 ──
    brand_id: Mapped[int | None] = mapped_column(ForeignKey("brands.id"), nullable=True)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    package_type: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # ── 电子属性 ──
    package_case: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )  # 封装类型 QFN-48 / SOT-23
    pin_count: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 引脚数
    voltage_rating: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )  # 电压规格
    tolerance_pct: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )  # 容差 ±1%
    temperature_range: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )  # 工作温度
    power_rating: Mapped[str | None] = mapped_column(String(50), nullable=True)  # 功率

    # ── 规格文本 ──
    specs: Mapped[str | None] = mapped_column(Text, nullable=True)
    unit: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # ── 物理属性 ──
    length_mm: Mapped[float | None] = mapped_column(DECIMAL(10, 3), nullable=True)
    width_mm: Mapped[float | None] = mapped_column(DECIMAL(10, 3), nullable=True)
    height_mm: Mapped[float | None] = mapped_column(DECIMAL(10, 3), nullable=True)
    gross_weight_g: Mapped[float | None] = mapped_column(DECIMAL(12, 3), nullable=True)
    net_weight_g: Mapped[float | None] = mapped_column(DECIMAL(12, 3), nullable=True)

    # ── 商务属性 ──
    tax_rate: Mapped[float | None] = mapped_column(
        DECIMAL(5, 2), nullable=True
    )  # 税率 %
    currency: Mapped[str] = mapped_column(String(3), default="CNY")  # 币种
    standard_cost: Mapped[float | None] = mapped_column(
        DECIMAL(20, 6), nullable=True
    )  # 标准成本
    list_price: Mapped[float | None] = mapped_column(
        DECIMAL(20, 6), nullable=True
    )  # 列表价
    wholesale_price: Mapped[float | None] = mapped_column(
        DECIMAL(20, 6), nullable=True
    )  # 批发价

    # ── 生命周期与合规 ──
    lifecycle_status: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )  # active / nrnd / eol / obsolete
    eol_date: Mapped[DateTime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )  # EOL 日期
    alternative_mpn: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )  # 替代型号 MPN
    rohs_compliant: Mapped[bool] = mapped_column(Boolean, default=True)
    reach_compliant: Mapped[bool] = mapped_column(Boolean, default=False)
    esd_sensitive: Mapped[bool] = mapped_column(Boolean, default=False)
    msl_level: Mapped[str | None] = mapped_column(
        String(5), nullable=True
    )  # 湿度敏感等级

    # ── 文档 ──
    datasheet_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    rohs_cert_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    reach_cert_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # ── 备注与向量 ──
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1536), nullable=True)

    brand = relationship("Brand", back_populates="products", lazy="selectin")
    quotation_items = relationship(
        "QuotationItem", back_populates="product", lazy="selectin"
    )
    sales_order_items = relationship(
        "SalesOrderItem", back_populates="product", lazy="selectin"
    )
    delivery_note_items = relationship(
        "DeliveryNoteItem", back_populates="product", lazy="selectin"
    )


class Supplier(TimestampMixin, Base):
    __tablename__ = "suppliers"

    name: Mapped[str] = mapped_column(String(255))
    contact_person: Mapped[str | None] = mapped_column(String(100), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    product_lines: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── 商务 ──
    supplier_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), default="active"
    )  # active / inactive / blacklisted
    payment_terms: Mapped[str | None] = mapped_column(String(100), nullable=True)
    payment_method: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )  # T/T / L/C / net30
    currency: Mapped[str] = mapped_column(String(3), default="CNY")
    incoterms: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )  # FOB / CIF / EXW / DDP

    # ── 资质 ──
    certifications: Mapped[str | None] = mapped_column(Text, nullable=True)
    financial_rating: Mapped[str | None] = mapped_column(String(10), nullable=True)
    rating_score: Mapped[float | None] = mapped_column(
        DECIMAL(3, 1), nullable=True
    )  # 1.0–5.0

    # ── 供应链 ──
    region: Mapped[str | None] = mapped_column(String(50), nullable=True)
    website: Mapped[str | None] = mapped_column(String(255), nullable=True)
    lead_time_days: Mapped[int | None] = mapped_column(nullable=True)
    min_order_value: Mapped[float | None] = mapped_column(DECIMAL(18, 2), nullable=True)
    last_audit_date: Mapped[DateTime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # ── AI ──
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1536), nullable=True)
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    updated_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )

    supplier_products = relationship(
        "SupplierProduct", foreign_keys="SupplierProduct.supplier_id", lazy="selectin"
    )


class Warehouse(TimestampMixin, Base):
    __tablename__ = "warehouses"

    name: Mapped[str] = mapped_column(String(100))
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    warehouse_type: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )  # main / transit / returns / quarantine
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    updated_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )


class Inventory(TimestampMixin, Base):
    __tablename__ = "inventories"

    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouses.id"))
    quantity: Mapped[int] = mapped_column(default=0)
    safety_stock: Mapped[int] = mapped_column(default=0)
    locked_quantity: Mapped[int] = mapped_column(default=0)
    unit_price: Mapped[float | None] = mapped_column(
        DECIMAL(20, 6), nullable=True, default=None
    )

    # ── 库位 ──
    location_code: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )  # 库位编码 e.g. A-01-03

    # ── 补货参数 ──
    reorder_point: Mapped[int] = mapped_column(default=0)  # 再订货点
    max_stock: Mapped[int | None] = mapped_column(nullable=True)  # 最大库存

    # ── 库存分类 ──
    abc_class: Mapped[str | None] = mapped_column(
        String(1), nullable=True
    )  # A / B / C — 按库存价值分级
    costing_method: Mapped[str] = mapped_column(
        String(20), default="moving_avg"
    )  # fifo / weighted_avg / moving_avg

    # ── 盘点 ──
    last_counted_at: Mapped[DateTime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )  # 上次盘点日期
    count_cycle_days: Mapped[int | None] = mapped_column(
        nullable=True
    )  # 盘点周期（天）

    # ── 乐观锁 ──
    version: Mapped[int] = mapped_column(default=0, nullable=False)
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    updated_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )


class InventoryBatchORM(TimestampMixin, Base):
    """One row per receipt batch — traceability for ROHS / MSL / perishable items.

    Each batch has its own quantity, cost, expiry. The application
    layer uses FEFO allocation to pick which batch to deduct from.
    """

    __tablename__ = "inventory_batches"
    __table_args__ = (
        UniqueConstraint(
            "product_id", "warehouse_id", "batch_no", name="uq_inv_batch_pkey"
        ),
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
    expiry_date: Mapped[DateTime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    manufacture_date: Mapped[DateTime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    supplier_id: Mapped[int | None] = mapped_column(
        ForeignKey("suppliers.id"), nullable=True
    )
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
    type: Mapped[str] = mapped_column(
        String(20)
    )  # stock_in, stock_out, adjust, transfer
    quantity: Mapped[int] = mapped_column()
    before_qty: Mapped[int | None] = mapped_column(nullable=True)
    after_qty: Mapped[int | None] = mapped_column(nullable=True)
    reference_type: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )  # purchase, sales_order, manual
    reference_id: Mapped[int | None] = mapped_column(nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class SupplierProduct(TimestampMixin, Base):
    __tablename__ = "supplier_products"

    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.id"))
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))

    # ── 价格与数量 ──
    cost_price: Mapped[float | None] = mapped_column(DECIMAL(20, 6), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="CNY")
    price_valid_from: Mapped[DateTime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    price_valid_to: Mapped[DateTime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    moq: Mapped[int | None] = mapped_column(nullable=True)  # minimum order quantity
    spq: Mapped[int | None] = mapped_column(nullable=True)  # standard package quantity
    min_order_value: Mapped[float | None] = mapped_column(DECIMAL(18, 2), nullable=True)

    # ── 交付 ──
    lead_time_days: Mapped[int | None] = mapped_column(nullable=True)
    supplier_sku: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )  # 供应商自己的编码

    # ── 状态 ──
    is_preferred: Mapped[bool] = mapped_column(default=False)
    is_active: Mapped[bool] = mapped_column(default=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    updated_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )


# ══════════════════════════════════════════════════════════════════════════════
# BOM — Bill of Materials (物料清单)
# ══════════════════════════════════════════════════════════════════════════════


class BOM(TimestampMixin, Base):
    """Bill of Materials header — defines an assembly structure.

    A product (assembly) has one active BOM at a time (enforced by
    application-layer version management).  Multi-level BOMs are
    supported: a BOM line may reference a child product that itself
    has a BOM.
    """

    __tablename__ = "boms"

    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    name: Mapped[str] = mapped_column(String(255))  # e.g. "PCB Assembly v1.2"
    version: Mapped[str] = mapped_column(String(20), default="1.0")
    status: Mapped[str] = mapped_column(
        String(20), default="draft"
    )  # draft / active / obsolete
    revision_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    updated_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )

    product = relationship("Product", foreign_keys=[product_id])
    lines = relationship(
        "BOMLine", back_populates="bom", lazy="selectin", cascade="all, delete-orphan"
    )


class BOMLine(TimestampMixin, Base):
    """Single line in a BOM — one component used in an assembly."""

    __tablename__ = "bom_lines"

    bom_id: Mapped[int] = mapped_column(ForeignKey("boms.id"))
    child_product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    quantity: Mapped[float] = mapped_column(DECIMAL(12, 4), default=1)  # per assembly
    unit: Mapped[str | None] = mapped_column(String(20), nullable=True)
    reference_designator: Mapped[str | None] = mapped_column(
        String(200), nullable=True
    )  # e.g. "R1,R2,R3" or "U1"
    position: Mapped[int] = mapped_column(default=0)  # line sort order
    is_critical: Mapped[bool] = mapped_column(default=False)  # critical component flag
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    bom = relationship("BOM", back_populates="lines")
    child_product = relationship("Product", foreign_keys=[child_product_id])
