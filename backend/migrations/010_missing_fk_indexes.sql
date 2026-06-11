-- 010_missing_fk_indexes.sql
-- Add indexes on FK columns that are missing them.
-- Each index uses partial WHERE deleted_at IS NULL to stay lean.

-- Sales pipeline: customer FKs (most queried)
CREATE INDEX IF NOT EXISTS idx_invoices_customer_id        ON invoices(customer_id)        WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_invoices_sales_order_id     ON invoices(sales_order_id)     WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_payment_records_customer_id ON payment_records(customer_id) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_payment_records_sales_order ON payment_records(sales_order_id) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_quotations_customer_id      ON quotations(customer_id)      WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_sales_orders_customer_id    ON sales_orders(customer_id)    WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_opportunities_customer_id   ON opportunities(customer_id)   WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_opportunities_status        ON opportunities(status)        WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_delivery_notes_sales_order  ON delivery_notes(sales_order_id) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_contracts_customer_id       ON contracts(customer_id)       WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_contracts_sales_order_id    ON contracts(sales_order_id)    WHERE deleted_at IS NULL;

-- Procurement
CREATE INDEX IF NOT EXISTS idx_purchase_orders_supplier_id ON purchase_orders(supplier_id) WHERE deleted_at IS NULL;

-- Sales order items (frequent JOIN target)
CREATE INDEX IF NOT EXISTS idx_sales_order_items_order_id  ON sales_order_items(order_id)  WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_quotation_items_quotation   ON quotation_items(quotation_id) WHERE deleted_at IS NULL;

-- Delivery items
CREATE INDEX IF NOT EXISTS idx_delivery_note_items_note    ON delivery_note_items(delivery_note_id) WHERE deleted_at IS NULL;

-- Invoice lines
CREATE INDEX IF NOT EXISTS idx_invoice_lines_product       ON invoice_lines(product_id)    WHERE deleted_at IS NULL;

-- Composite: payment status + date (dashboard/summary queries)
CREATE INDEX IF NOT EXISTS idx_payment_records_status_date ON payment_records(status, payment_date) WHERE deleted_at IS NULL;

-- Composite: invoice status + due_date (AR aging)
CREATE INDEX IF NOT EXISTS idx_invoices_status_duedate     ON invoices(status, due_date)   WHERE deleted_at IS NULL;
