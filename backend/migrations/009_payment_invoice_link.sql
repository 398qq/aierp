-- 009_payment_invoice_link.sql
-- Add invoice_id FK to payment_records for Payment ↔ Invoice reconciliation.

ALTER TABLE payment_records
    ADD COLUMN IF NOT EXISTS invoice_id BIGINT REFERENCES invoices(id);

CREATE INDEX IF NOT EXISTS idx_payment_records_invoice_id
    ON payment_records(invoice_id)
    WHERE invoice_id IS NOT NULL AND deleted_at IS NULL;
