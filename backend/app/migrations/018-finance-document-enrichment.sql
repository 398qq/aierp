-- 018: Finance document enrichment — invoice lines, currency, due dates
BEGIN;

-- ═══════════════════════════════════════════════════════════════════════════
-- Invoice
-- ═══════════════════════════════════════════════════════════════════════════
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS currency VARCHAR(3)  NOT NULL DEFAULT 'CNY';
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS due_date TIMESTAMPTZ;
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS subtotal DECIMAL(20,6);

-- ═══════════════════════════════════════════════════════════════════════════
-- InvoiceLine
-- ═══════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS invoice_lines (
    id              SERIAL PRIMARY KEY,
    invoice_id      INTEGER NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,
    product_id      INTEGER REFERENCES products(id),
    product_name    VARCHAR(255),
    quantity        INTEGER  NOT NULL DEFAULT 1,
    unit            VARCHAR(20),
    unit_price      DECIMAL(20,6),
    total_price     DECIMAL(20,6),
    tax_rate        DECIMAL(5,2),
    tax_amount      DECIMAL(20,6),
    notes           TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ,
    deleted_at      TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_invoice_lines_invoice ON invoice_lines (invoice_id) WHERE deleted_at IS NULL;

-- ═══════════════════════════════════════════════════════════════════════════
-- PaymentRecord
-- ═══════════════════════════════════════════════════════════════════════════
ALTER TABLE payment_records ADD COLUMN IF NOT EXISTS currency       VARCHAR(3)  NOT NULL DEFAULT 'CNY';
ALTER TABLE payment_records ADD COLUMN IF NOT EXISTS transaction_ref VARCHAR(100);
ALTER TABLE payment_records ADD COLUMN IF NOT EXISTS bank_account   VARCHAR(50);

-- ═══════════════════════════════════════════════════════════════════════════
-- Contract
-- ═══════════════════════════════════════════════════════════════════════════
ALTER TABLE contracts ADD COLUMN IF NOT EXISTS currency VARCHAR(3) NOT NULL DEFAULT 'CNY';

COMMIT;
