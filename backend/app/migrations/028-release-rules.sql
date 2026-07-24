-- Release rules for auto-releasing customer owners

CREATE TABLE IF NOT EXISTS release_rules (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    rule_type VARCHAR(50) NOT NULL,  -- no_followup, no_order
    condition_days INTEGER NOT NULL DEFAULT 90,
    target_status VARCHAR(20),
    is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    priority INTEGER NOT NULL DEFAULT 0,
    notify_owner BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    deleted_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_release_rules_enabled ON release_rules(is_enabled, priority);
