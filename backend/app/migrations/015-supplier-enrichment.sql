-- 015: Supplier & SupplierProduct enrichment — professional procurement fields
BEGIN;

-- ═══════════════════════════════════════════════════════════════════════════
-- Supplier
-- ═══════════════════════════════════════════════════════════════════════════
ALTER TABLE suppliers ADD COLUMN IF NOT EXISTS status          VARCHAR(20)  NOT NULL DEFAULT 'active';   -- active / inactive / blacklisted
ALTER TABLE suppliers ADD COLUMN IF NOT EXISTS payment_method  VARCHAR(50);      -- T/T / L/C / net30
ALTER TABLE suppliers ADD COLUMN IF NOT EXISTS currency        VARCHAR(3)   NOT NULL DEFAULT 'CNY';
ALTER TABLE suppliers ADD COLUMN IF NOT EXISTS incoterms       VARCHAR(20);      -- FOB / CIF / EXW / DDP
ALTER TABLE suppliers ADD COLUMN IF NOT EXISTS rating_score    DECIMAL(3,1);     -- 1.0 – 5.0
ALTER TABLE suppliers ADD COLUMN IF NOT EXISTS lead_time_days  INTEGER;
ALTER TABLE suppliers ADD COLUMN IF NOT EXISTS min_order_value DECIMAL(18,2);
ALTER TABLE suppliers ADD COLUMN IF NOT EXISTS last_audit_date TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_suppliers_status ON suppliers (status) WHERE deleted_at IS NULL;

-- ═══════════════════════════════════════════════════════════════════════════
-- SupplierProduct
-- ═══════════════════════════════════════════════════════════════════════════
ALTER TABLE supplier_products ADD COLUMN IF NOT EXISTS currency         VARCHAR(3)  NOT NULL DEFAULT 'CNY';
ALTER TABLE supplier_products ADD COLUMN IF NOT EXISTS price_valid_from TIMESTAMPTZ;
ALTER TABLE supplier_products ADD COLUMN IF NOT EXISTS price_valid_to   TIMESTAMPTZ;
ALTER TABLE supplier_products ADD COLUMN IF NOT EXISTS min_order_value  DECIMAL(18,2);
ALTER TABLE supplier_products ADD COLUMN IF NOT EXISTS supplier_sku     VARCHAR(100);
ALTER TABLE supplier_products ADD COLUMN IF NOT EXISTS is_active        BOOLEAN NOT NULL DEFAULT TRUE;

CREATE INDEX IF NOT EXISTS idx_supplier_products_active ON supplier_products (is_active) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_supplier_products_sku    ON supplier_products (supplier_sku) WHERE deleted_at IS NULL;

COMMIT;
