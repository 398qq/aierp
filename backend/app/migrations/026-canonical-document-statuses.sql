-- Normalize legacy document status values to the canonical state-machine vocabulary.
UPDATE quotations SET status = 'won' WHERE status = 'converted';
UPDATE delivery_notes SET status = 'delivered' WHERE status = 'received';
