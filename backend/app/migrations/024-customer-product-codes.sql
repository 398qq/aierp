-- 024: Customer-specific product identities and sales document snapshots
BEGIN;

CREATE TABLE IF NOT EXISTS customer_product_codes (
    id BIGSERIAL PRIMARY KEY,
    customer_id BIGINT NOT NULL REFERENCES customers(id),
    product_id BIGINT NOT NULL REFERENCES products(id),
    customer_part_no VARCHAR(150) NOT NULL,
    customer_product_name VARCHAR(255),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    notes TEXT,
    created_by BIGINT REFERENCES users(id),
    updated_by BIGINT REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ,
    deleted_at TIMESTAMPTZ
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_customer_product_code_product
    ON customer_product_codes(customer_id, product_id) WHERE deleted_at IS NULL;
CREATE UNIQUE INDEX IF NOT EXISTS uq_customer_product_code_part_no
    ON customer_product_codes(customer_id, customer_part_no) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_customer_product_codes_product
    ON customer_product_codes(product_id) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_customer_product_codes_customer
    ON customer_product_codes(customer_id) WHERE deleted_at IS NULL;

ALTER TABLE quotation_items ADD COLUMN IF NOT EXISTS customer_part_no VARCHAR(150);
ALTER TABLE quotation_items ADD COLUMN IF NOT EXISTS customer_product_name VARCHAR(255);
ALTER TABLE sales_order_items ADD COLUMN IF NOT EXISTS customer_part_no VARCHAR(150);
ALTER TABLE sales_order_items ADD COLUMN IF NOT EXISTS customer_product_name VARCHAR(255);
ALTER TABLE delivery_note_items ADD COLUMN IF NOT EXISTS customer_part_no VARCHAR(150);
ALTER TABLE delivery_note_items ADD COLUMN IF NOT EXISTS customer_product_name VARCHAR(255);

COMMIT;
