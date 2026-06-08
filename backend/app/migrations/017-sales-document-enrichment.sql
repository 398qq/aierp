-- 017: Sales document enrichment — professional order-to-cash fields
BEGIN;

-- ═══════════════════════════════════════════════════════════════════════════
-- Quotation
-- ═══════════════════════════════════════════════════════════════════════════
ALTER TABLE quotations ADD COLUMN IF NOT EXISTS currency        VARCHAR(3)  NOT NULL DEFAULT 'CNY';
ALTER TABLE quotations ADD COLUMN IF NOT EXISTS incoterms       VARCHAR(20);
ALTER TABLE quotations ADD COLUMN IF NOT EXISTS payment_terms   VARCHAR(100);
ALTER TABLE quotations ADD COLUMN IF NOT EXISTS discount_rate   DECIMAL(5,2);
ALTER TABLE quotations ADD COLUMN IF NOT EXISTS discount_amount DECIMAL(20,6);
ALTER TABLE quotations ADD COLUMN IF NOT EXISTS subtotal        DECIMAL(20,6);

-- ═══════════════════════════════════════════════════════════════════════════
-- QuotationItem
-- ═══════════════════════════════════════════════════════════════════════════
ALTER TABLE quotation_items ADD COLUMN IF NOT EXISTS unit          VARCHAR(20);
ALTER TABLE quotation_items ADD COLUMN IF NOT EXISTS tax_rate      DECIMAL(5,2);
ALTER TABLE quotation_items ADD COLUMN IF NOT EXISTS discount_rate DECIMAL(5,2);

-- ═══════════════════════════════════════════════════════════════════════════
-- SalesOrder
-- ═══════════════════════════════════════════════════════════════════════════
ALTER TABLE sales_orders ADD COLUMN IF NOT EXISTS currency         VARCHAR(3)  NOT NULL DEFAULT 'CNY';
ALTER TABLE sales_orders ADD COLUMN IF NOT EXISTS incoterms        VARCHAR(20);
ALTER TABLE sales_orders ADD COLUMN IF NOT EXISTS payment_terms    VARCHAR(100);
ALTER TABLE sales_orders ADD COLUMN IF NOT EXISTS due_date         TIMESTAMPTZ;
ALTER TABLE sales_orders ADD COLUMN IF NOT EXISTS customer_po_no   VARCHAR(100);
ALTER TABLE sales_orders ADD COLUMN IF NOT EXISTS shipping_address TEXT;
ALTER TABLE sales_orders ADD COLUMN IF NOT EXISTS billing_address  TEXT;
ALTER TABLE sales_orders ADD COLUMN IF NOT EXISTS discount_rate    DECIMAL(5,2);
ALTER TABLE sales_orders ADD COLUMN IF NOT EXISTS discount_amount  DECIMAL(20,6);
ALTER TABLE sales_orders ADD COLUMN IF NOT EXISTS subtotal         DECIMAL(20,6);

-- ═══════════════════════════════════════════════════════════════════════════
-- SalesOrderItem
-- ═══════════════════════════════════════════════════════════════════════════
ALTER TABLE sales_order_items ADD COLUMN IF NOT EXISTS unit          VARCHAR(20);
ALTER TABLE sales_order_items ADD COLUMN IF NOT EXISTS tax_rate      DECIMAL(5,2);
ALTER TABLE sales_order_items ADD COLUMN IF NOT EXISTS discount_rate DECIMAL(5,2);

-- ═══════════════════════════════════════════════════════════════════════════
-- DeliveryNote
-- ═══════════════════════════════════════════════════════════════════════════
ALTER TABLE delivery_notes ADD COLUMN IF NOT EXISTS shipping_method VARCHAR(50);
ALTER TABLE delivery_notes ADD COLUMN IF NOT EXISTS tracking_number VARCHAR(100);
ALTER TABLE delivery_notes ADD COLUMN IF NOT EXISTS incoterms       VARCHAR(20);

-- ═══════════════════════════════════════════════════════════════════════════
-- DeliveryNoteItem
-- ═══════════════════════════════════════════════════════════════════════════
ALTER TABLE delivery_note_items ADD COLUMN IF NOT EXISTS unit VARCHAR(20);

-- ═══════════════════════════════════════════════════════════════════════════
-- Indexes
-- ═══════════════════════════════════════════════════════════════════════════
CREATE INDEX IF NOT EXISTS idx_sales_orders_po_no ON sales_orders (customer_po_no) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_delivery_notes_tracking ON delivery_notes (tracking_number) WHERE deleted_at IS NULL;

COMMIT;
