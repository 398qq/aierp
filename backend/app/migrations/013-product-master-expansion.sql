-- 013: Product master data expansion — professional ERP attributes
-- Adds 29 fields across identifiers, electronics, physical, business,
-- lifecycle, compliance, and documentation categories.
BEGIN;

-- ── 基础标识 ──
ALTER TABLE products ADD COLUMN IF NOT EXISTS mpn            VARCHAR(100);
ALTER TABLE products ADD COLUMN IF NOT EXISTS barcode        VARCHAR(50);
ALTER TABLE products ADD COLUMN IF NOT EXISTS hs_code        VARCHAR(20);
ALTER TABLE products ADD COLUMN IF NOT EXISTS origin_country VARCHAR(50);

-- ── 电子属性 ──
ALTER TABLE products ADD COLUMN IF NOT EXISTS package_case      VARCHAR(50);
ALTER TABLE products ADD COLUMN IF NOT EXISTS pin_count         INTEGER;
ALTER TABLE products ADD COLUMN IF NOT EXISTS voltage_rating    VARCHAR(50);
ALTER TABLE products ADD COLUMN IF NOT EXISTS tolerance_pct     VARCHAR(50);
ALTER TABLE products ADD COLUMN IF NOT EXISTS temperature_range VARCHAR(50);
ALTER TABLE products ADD COLUMN IF NOT EXISTS power_rating      VARCHAR(50);

-- ── 物理属性 ──
ALTER TABLE products ADD COLUMN IF NOT EXISTS length_mm      DECIMAL(10, 3);
ALTER TABLE products ADD COLUMN IF NOT EXISTS width_mm       DECIMAL(10, 3);
ALTER TABLE products ADD COLUMN IF NOT EXISTS height_mm      DECIMAL(10, 3);
ALTER TABLE products ADD COLUMN IF NOT EXISTS gross_weight_g DECIMAL(12, 3);
ALTER TABLE products ADD COLUMN IF NOT EXISTS net_weight_g   DECIMAL(12, 3);

-- ── 商务属性 ──
ALTER TABLE products ADD COLUMN IF NOT EXISTS tax_rate        DECIMAL(5, 2);
ALTER TABLE products ADD COLUMN IF NOT EXISTS currency        VARCHAR(3)  NOT NULL DEFAULT 'CNY';
ALTER TABLE products ADD COLUMN IF NOT EXISTS standard_cost   DECIMAL(20, 6);
ALTER TABLE products ADD COLUMN IF NOT EXISTS list_price      DECIMAL(20, 6);
ALTER TABLE products ADD COLUMN IF NOT EXISTS wholesale_price DECIMAL(20, 6);

-- ── 生命周期与合规 ──
ALTER TABLE products ADD COLUMN IF NOT EXISTS lifecycle_status VARCHAR(20);     -- active / nrnd / eol / obsolete
ALTER TABLE products ADD COLUMN IF NOT EXISTS eol_date          TIMESTAMPTZ;
ALTER TABLE products ADD COLUMN IF NOT EXISTS alternative_mpn   VARCHAR(100);
ALTER TABLE products ADD COLUMN IF NOT EXISTS rohs_compliant    BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE products ADD COLUMN IF NOT EXISTS reach_compliant   BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE products ADD COLUMN IF NOT EXISTS esd_sensitive     BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE products ADD COLUMN IF NOT EXISTS msl_level         VARCHAR(5);         -- MSL 1 / 2 / 3 / 4 / 5 / 5A / 6

-- ── 文档 ──
ALTER TABLE products ADD COLUMN IF NOT EXISTS datasheet_url VARCHAR(500);
ALTER TABLE products ADD COLUMN IF NOT EXISTS rohs_cert_url  VARCHAR(500);
ALTER TABLE products ADD COLUMN IF NOT EXISTS reach_cert_url VARCHAR(500);

-- ── 索引 ──
CREATE INDEX IF NOT EXISTS idx_products_mpn        ON products (mpn)        WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_products_barcode    ON products (barcode)    WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_products_hs_code    ON products (hs_code)    WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_products_lifecycle  ON products (lifecycle_status) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_products_eol_date   ON products (eol_date)   WHERE deleted_at IS NULL;

COMMIT;
