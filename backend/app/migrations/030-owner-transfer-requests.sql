-- Owner transfer approval workflow
-- Tracks pending transfer requests between users

CREATE TABLE IF NOT EXISTS owner_transfer_requests (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id     INTEGER NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    from_owner      VARCHAR(100),
    to_owner        VARCHAR(100) NOT NULL,
    requested_by    VARCHAR(100) NOT NULL,
    status          VARCHAR(20) NOT NULL DEFAULT 'pending',  -- pending, approved, rejected, cancelled
    reason          TEXT,
    reviewed_by     VARCHAR(100),
    review_comment  TEXT,
    reviewed_at     DATETIME,
    created_at      DATETIME NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S', 'now')),
    updated_at      DATETIME NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_otr_customer ON owner_transfer_requests(customer_id);
CREATE INDEX IF NOT EXISTS idx_otr_status ON owner_transfer_requests(status);
CREATE INDEX IF NOT EXISTS idx_otr_requested_by ON owner_transfer_requests(requested_by);
