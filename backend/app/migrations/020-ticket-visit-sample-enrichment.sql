-- 020: Ticket/Visit/Sample enrichment — professional service fields
BEGIN;

ALTER TABLE tickets ADD COLUMN IF NOT EXISTS sla_deadline            TIMESTAMPTZ;
ALTER TABLE tickets ADD COLUMN IF NOT EXISTS root_cause              TEXT;
ALTER TABLE tickets ADD COLUMN IF NOT EXISTS resolution_time_minutes INTEGER;

ALTER TABLE visits ADD COLUMN IF NOT EXISTS visit_type        VARCHAR(30);
ALTER TABLE visits ADD COLUMN IF NOT EXISTS location          VARCHAR(255);
ALTER TABLE visits ADD COLUMN IF NOT EXISTS duration_minutes  INTEGER;
ALTER TABLE visits ADD COLUMN IF NOT EXISTS outcome           TEXT;
ALTER TABLE visits ADD COLUMN IF NOT EXISTS next_plan         TEXT;

ALTER TABLE samples ADD COLUMN IF NOT EXISTS status         VARCHAR(20)  NOT NULL DEFAULT 'pending';
ALTER TABLE samples ADD COLUMN IF NOT EXISTS tracking_no    VARCHAR(100);
ALTER TABLE samples ADD COLUMN IF NOT EXISTS approved_by    INTEGER REFERENCES users(id);
ALTER TABLE samples ADD COLUMN IF NOT EXISTS sample_result  TEXT;
ALTER TABLE samples ADD COLUMN IF NOT EXISTS shipped_date   TIMESTAMPTZ;
ALTER TABLE samples ADD COLUMN IF NOT EXISTS received_date  TIMESTAMPTZ;

COMMIT;
