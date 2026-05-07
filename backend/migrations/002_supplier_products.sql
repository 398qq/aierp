-- Migration: supplier_products table
CREATE TABLE IF NOT EXISTS supplier_products (
    id SERIAL PRIMARY KEY,
    supplier_id INTEGER NOT NULL REFERENCES suppliers(id),
    product_id INTEGER NOT NULL REFERENCES products(id),
    cost_price DECIMAL(12, 4),
    lead_time_days INTEGER,
    moq INTEGER,
    spq INTEGER,
    is_preferred BOOLEAN DEFAULT FALSE,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,
    UNIQUE(supplier_id, product_id, deleted_at)
);

CREATE INDEX IF NOT EXISTS idx_supplier_products_supplier ON supplier_products(supplier_id) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_supplier_products_product ON supplier_products(product_id) WHERE deleted_at IS NULL;
