-- Customer owner assignment history log
-- Tracks every claim / release / assign / auto_assign / auto_release action

CREATE TABLE IF NOT EXISTS customer_owner_logs (
    id SERIAL PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    from_owner VARCHAR(100),
    to_owner VARCHAR(100),
    action_type VARCHAR(30) NOT NULL,  -- claim, release, assign, auto_assign, transfer_in, transfer_out, auto_release
    operator VARCHAR(100),
    reason TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_customer_owner_logs_customer_id ON customer_owner_logs(customer_id);
CREATE INDEX idx_customer_owner_logs_created_at ON customer_owner_logs(created_at);
CREATE INDEX idx_customer_owner_logs_operator ON customer_owner_logs(operator);
