-- Assignment rules for auto-assigning customers to owners

CREATE TABLE IF NOT EXISTS assignment_rules (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    priority INTEGER NOT NULL DEFAULT 0,
    condition_logic VARCHAR(10) NOT NULL DEFAULT 'all',  -- all / any
    assigned_to VARCHAR(100) NOT NULL,
    max_customers INTEGER,
    is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    deleted_at TIMESTAMP WITH TIME ZONE
);

CREATE TABLE IF NOT EXISTS assignment_rule_conditions (
    id SERIAL PRIMARY KEY,
    rule_id INTEGER NOT NULL REFERENCES assignment_rules(id) ON DELETE CASCADE,
    field VARCHAR(50) NOT NULL,        -- industry, region, source, level, customer_type
    operator VARCHAR(20) NOT NULL,     -- equals, in, contains, not_empty
    value VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_assignment_rules_enabled ON assignment_rules(is_enabled, priority);
CREATE INDEX idx_assignment_rule_conditions_rule_id ON assignment_rule_conditions(rule_id);
