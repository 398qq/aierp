-- 023: Purchase order v3.4 operational and print snapshots
BEGIN;

ALTER TABLE purchase_orders ADD COLUMN IF NOT EXISTS supplier_contact VARCHAR(100);
ALTER TABLE purchase_orders ADD COLUMN IF NOT EXISTS sales_order_id BIGINT REFERENCES sales_orders(id);
ALTER TABLE purchase_orders ADD COLUMN IF NOT EXISTS delivery_address TEXT;
ALTER TABLE purchase_orders ADD COLUMN IF NOT EXISTS tax_rate DECIMAL(5,2) NOT NULL DEFAULT 13;
ALTER TABLE purchase_orders ADD COLUMN IF NOT EXISTS subtotal DECIMAL(20,6) NOT NULL DEFAULT 0;
ALTER TABLE purchase_orders ADD COLUMN IF NOT EXISTS tax_amount DECIMAL(20,6) NOT NULL DEFAULT 0;
ALTER TABLE purchase_orders ADD COLUMN IF NOT EXISTS large_order_confirmed BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE purchase_orders ADD COLUMN IF NOT EXISTS large_order_confirmed_at TIMESTAMPTZ;
ALTER TABLE purchase_orders ADD COLUMN IF NOT EXISTS supplier_confirmation_status VARCHAR(20) NOT NULL DEFAULT 'pending';
ALTER TABLE purchase_orders ADD COLUMN IF NOT EXISTS supplier_confirmed_at TIMESTAMPTZ;
ALTER TABLE purchase_orders ADD COLUMN IF NOT EXISTS supplier_confirmation_method VARCHAR(30);
ALTER TABLE purchase_orders ADD COLUMN IF NOT EXISTS supplier_confirmed_delivery_date TIMESTAMPTZ;
ALTER TABLE purchase_orders ADD COLUMN IF NOT EXISTS allow_partial_delivery BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE purchase_orders ADD COLUMN IF NOT EXISTS contract_terms_version VARCHAR(20) NOT NULL DEFAULT 'v3.4';
ALTER TABLE purchase_orders ADD COLUMN IF NOT EXISTS sent_at TIMESTAMPTZ;

ALTER TABLE purchase_order_items ADD COLUMN IF NOT EXISTS sales_order_id BIGINT REFERENCES sales_orders(id);
ALTER TABLE purchase_order_items ADD COLUMN IF NOT EXISTS supplier_mpn VARCHAR(150);
ALTER TABLE purchase_order_items ADD COLUMN IF NOT EXISTS product_sku VARCHAR(100);
ALTER TABLE purchase_order_items ADD COLUMN IF NOT EXISTS product_name VARCHAR(255);
ALTER TABLE purchase_order_items ADD COLUMN IF NOT EXISTS brand_name VARCHAR(255);
ALTER TABLE purchase_order_items ADD COLUMN IF NOT EXISTS package_type VARCHAR(100);
ALTER TABLE purchase_order_items ADD COLUMN IF NOT EXISTS min_pack_qty INTEGER;
ALTER TABLE purchase_order_items ADD COLUMN IF NOT EXISTS min_pack_unit VARCHAR(30);
ALTER TABLE purchase_order_items ADD COLUMN IF NOT EXISTS date_code_requirement VARCHAR(100) NOT NULL DEFAULT '不限';
ALTER TABLE purchase_order_items ADD COLUMN IF NOT EXISTS customer_name VARCHAR(255);
ALTER TABLE purchase_order_items ADD COLUMN IF NOT EXISTS notes TEXT;

CREATE INDEX IF NOT EXISTS idx_purchase_orders_sales_order_id ON purchase_orders(sales_order_id);
CREATE INDEX IF NOT EXISTS idx_purchase_order_items_sales_order_id ON purchase_order_items(sales_order_id);

COMMIT;
