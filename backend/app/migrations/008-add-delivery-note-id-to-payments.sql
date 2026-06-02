-- Migration 008: Add delivery_note_id to payment_records
-- Links payments to specific delivery notes for proper ERP flow.

ALTER TABLE payment_records ADD COLUMN IF NOT EXISTS delivery_note_id BIGINT REFERENCES delivery_notes(id);
CREATE INDEX IF NOT EXISTS idx_payment_records_delivery_note_id ON payment_records(delivery_note_id);
