-- 014: Inventory & BOM expansion — professional WMS + manufacturing
--   Warehouse: type, is_active
--   Inventory: location_code, reorder_point, max_stock, abc_class,
--              costing_method, last_counted_at, count_cycle_days
--   BOM: bill of materials (header + lines)
BEGIN;

-- ═══════════════════════════════════════════════════════════════════════════
-- Warehouse
-- ═══════════════════════════════════════════════════════════════════════════
ALTER TABLE warehouses ADD COLUMN IF NOT EXISTS warehouse_type VARCHAR(20);   -- main / transit / returns / quarantine
ALTER TABLE warehouses ADD COLUMN IF NOT EXISTS is_active      BOOLEAN NOT NULL DEFAULT TRUE;

-- ═══════════════════════════════════════════════════════════════════════════
-- Inventory
-- ═══════════════════════════════════════════════════════════════════════════
ALTER TABLE inventories ADD COLUMN IF NOT EXISTS location_code  VARCHAR(50);       -- 库位编码 A-01-03
ALTER TABLE inventories ADD COLUMN IF NOT EXISTS reorder_point  INTEGER  NOT NULL DEFAULT 0;   -- 再订货点
ALTER TABLE inventories ADD COLUMN IF NOT EXISTS max_stock      INTEGER;            -- 最大库存
ALTER TABLE inventories ADD COLUMN IF NOT EXISTS abc_class      VARCHAR(1);         -- A / B / C
ALTER TABLE inventories ADD COLUMN IF NOT EXISTS costing_method VARCHAR(20) NOT NULL DEFAULT 'moving_avg';  -- fifo / weighted_avg / moving_avg
ALTER TABLE inventories ADD COLUMN IF NOT EXISTS last_counted_at  TIMESTAMPTZ;      -- 上次盘点
ALTER TABLE inventories ADD COLUMN IF NOT EXISTS count_cycle_days INTEGER;          -- 盘点周期（天）

CREATE INDEX IF NOT EXISTS idx_inventories_location ON inventories (location_code) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_inventories_abc       ON inventories (abc_class)     WHERE deleted_at IS NULL;

-- ═══════════════════════════════════════════════════════════════════════════
-- BOM — Bill of Materials
-- ═══════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS boms (
    id              SERIAL PRIMARY KEY,
    product_id      INTEGER  NOT NULL REFERENCES products(id),
    name            VARCHAR(255) NOT NULL,
    version         VARCHAR(20)  NOT NULL DEFAULT '1.0',
    status          VARCHAR(20)  NOT NULL DEFAULT 'draft',     -- draft / active / obsolete
    revision_notes  TEXT,
    created_by      INTEGER REFERENCES users(id),
    updated_by      INTEGER REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ,
    deleted_at      TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_boms_product ON boms (product_id) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_boms_status   ON boms (status)     WHERE deleted_at IS NULL;

CREATE TABLE IF NOT EXISTS bom_lines (
    id                  SERIAL PRIMARY KEY,
    bom_id              INTEGER NOT NULL REFERENCES boms(id) ON DELETE CASCADE,
    child_product_id    INTEGER NOT NULL REFERENCES products(id),
    quantity            DECIMAL(12,4) NOT NULL DEFAULT 1,
    unit                VARCHAR(20),
    reference_designator VARCHAR(200),         -- "R1,R2,R3"
    position            INTEGER  NOT NULL DEFAULT 0,
    is_critical         BOOLEAN  NOT NULL DEFAULT FALSE,
    notes               TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ,
    deleted_at          TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_bom_lines_bom     ON bom_lines (bom_id)           WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_bom_lines_product ON bom_lines (child_product_id) WHERE deleted_at IS NULL;

COMMIT;
