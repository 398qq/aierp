-- 019: Purchase order enrichment — procurement fields
BEGIN;

ALTER TABLE purchase_orders ADD COLUMN IF NOT EXISTS currency      VARCHAR(3)  NOT NULL DEFAULT 'CNY';
ALTER TABLE purchase_orders ADD COLUMN IF NOT EXISTS incoterms     VARCHAR(20);
ALTER TABLE purchase_orders ADD COLUMN IF NOT EXISTS payment_terms VARCHAR(100);

ALTER TABLE purchase_order_items ADD COLUMN IF NOT EXISTS unit     VARCHAR(20);
ALTER TABLE purchase_order_items ADD COLUMN IF NOT EXISTS tax_rate DECIMAL(5,2);

COMMIT;
