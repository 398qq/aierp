-- 006-phase6-finance.sql
-- Phase 6: Finance Enhancement — Chart of Accounts, Journal Entries, Bank Reconciliation
-- Plus: Notification Templates, User Preferences, Integration Configs

-- ============================================================
-- Chart of Accounts
-- ============================================================
CREATE TABLE IF NOT EXISTS accounts (
    id SERIAL PRIMARY KEY,
    code VARCHAR(30) NOT NULL,
    name VARCHAR(100) NOT NULL,
    type VARCHAR(20) NOT NULL CHECK (type IN ('asset','liability','equity','income','expense')),
    parent_id INTEGER REFERENCES accounts(id),
    description TEXT,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_accounts_code ON accounts(code) WHERE deleted_at IS NULL;

-- ============================================================
-- Journal Entries (凭证头)
-- ============================================================
CREATE TABLE IF NOT EXISTS journal_entries (
    id SERIAL PRIMARY KEY,
    entry_no VARCHAR(50) NOT NULL,
    entry_date DATE NOT NULL DEFAULT CURRENT_DATE,
    description TEXT,
    status VARCHAR(20) DEFAULT 'draft' CHECK (status IN ('draft','posted','reversed')),
    created_by INTEGER REFERENCES users(id),
    posted_at TIMESTAMPTZ,
    posted_by INTEGER REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_journal_entries_no ON journal_entries(entry_no) WHERE deleted_at IS NULL;

-- ============================================================
-- Journal Entry Lines (凭证行)
-- ============================================================
CREATE TABLE IF NOT EXISTS journal_entry_lines (
    id SERIAL PRIMARY KEY,
    entry_id INTEGER NOT NULL REFERENCES journal_entries(id),
    account_id INTEGER NOT NULL REFERENCES accounts(id),
    description TEXT,
    debit DECIMAL(15,2) DEFAULT 0,
    credit DECIMAL(15,2) DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

-- ============================================================
-- Bank Reconciliations (银行对账)
-- ============================================================
CREATE TABLE IF NOT EXISTS bank_reconciliations (
    id SERIAL PRIMARY KEY,
    payment_id INTEGER REFERENCES payment_records(id),
    bank_txn_id VARCHAR(100),
    bank_date DATE,
    bank_amount DECIMAL(15,2),
    bank_description TEXT,
    match_type VARCHAR(20) DEFAULT 'auto' CHECK (match_type IN ('auto','manual','unmatched')),
    difference DECIMAL(15,2) DEFAULT 0,
    reconciled_by INTEGER REFERENCES users(id),
    reconciled_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

-- ============================================================
-- Notification Templates
-- ============================================================
CREATE TABLE IF NOT EXISTS notification_templates (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    channel VARCHAR(30) DEFAULT 'in_app' CHECK (channel IN ('in_app','email','wecom_webhook')),
    event_type VARCHAR(50) NOT NULL,
    subject_template VARCHAR(255),
    body_template TEXT NOT NULL,
    enabled BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

-- ============================================================
-- Notification Preferences (user-level)
-- ============================================================
CREATE TABLE IF NOT EXISTS notification_preferences (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    event_type VARCHAR(50) NOT NULL,
    channel VARCHAR(30) DEFAULT 'in_app',
    enabled BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,
    UNIQUE(user_id, event_type, channel)
);

-- ============================================================
-- Integration Configs (外部集成)
-- ============================================================
CREATE TABLE IF NOT EXISTS integration_configs (
    id SERIAL PRIMARY KEY,
    type VARCHAR(30) NOT NULL CHECK (type IN ('ecommerce','logistics','webhook','email')),
    name VARCHAR(100) NOT NULL,
    api_key_encrypted TEXT,
    api_secret_encrypted TEXT,
    endpoint VARCHAR(500),
    settings JSONB DEFAULT '{}',
    enabled BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

-- ============================================================
-- Alter existing tables
-- ============================================================
-- Add notification channel fields (if not exists)
ALTER TABLE notifications ADD COLUMN IF NOT EXISTS channel VARCHAR(30) DEFAULT 'in_app';
ALTER TABLE notifications ADD COLUMN IF NOT EXISTS template_code VARCHAR(50);
ALTER TABLE notifications ADD COLUMN IF NOT EXISTS external_id VARCHAR(100);

-- Add logistics fields to purchase_orders
ALTER TABLE purchase_orders ADD COLUMN IF NOT EXISTS logistics_no VARCHAR(100);
ALTER TABLE purchase_orders ADD COLUMN IF NOT EXISTS logistics_provider VARCHAR(50);

-- ============================================================
-- Seed: Default Chart of Accounts
-- ============================================================
INSERT INTO accounts (code, name, type, description) VALUES
    -- Assets
    ('1001', '库存现金', 'asset', '现金'),
    ('1002', '银行存款', 'asset', '银行存款'),
    ('1122', '应收账款', 'asset', '应收客户货款'),
    ('1403', '库存商品', 'asset', '库存商品'),
    -- Liabilities
    ('2001', '短期借款', 'liability', '短期借款'),
    ('2202', '应付账款', 'liability', '应付供应商货款'),
    ('2221', '应交税费', 'liability', '应交税费'),
    -- Equity
    ('3001', '实收资本', 'equity', '实收资本'),
    ('3101', '未分配利润', 'equity', '未分配利润'),
    -- Income
    ('4001', '主营业务收入', 'income', '销售收入'),
    ('4002', '其他业务收入', 'income', '其他收入'),
    -- Expense
    ('5001', '主营业务成本', 'expense', '销售成本'),
    ('5002', '管理费用', 'expense', '管理费用'),
    ('5003', '销售费用', 'expense', '销售费用'),
    ('5004', '财务费用', 'expense', '财务费用')
ON CONFLICT (code) DO NOTHING;

-- ============================================================
-- Seed: Default Notification Templates
-- ============================================================
INSERT INTO notification_templates (code, name, channel, event_type, subject_template, body_template) VALUES
    ('approval_request', '审批请求', 'in_app', 'approval_requested',
     '新的审批请求: {{doc_type}} #{{doc_id}}',
     '{{submitter}} 提交了 {{doc_type}} #{{doc_id}} 的审批请求，金额 ¥{{amount}}，请审批。'),
    ('approval_result', '审批结果', 'in_app', 'approval_completed',
     '审批结果: {{doc_type}} #{{doc_id}}',
     '您的 {{doc_type}} #{{doc_id}} 审批{{result}}。{{comment}}'),
    ('daily_report', '日报摘要', 'in_app', 'daily_report',
     'AIERP 经营日报 — {{report_date}}',
     '今日销售: ¥{{revenue}} | 新客户: {{new_customers}} | 回款: ¥{{payments}} | 库存预警: {{stock_alerts}}'),
    ('stock_alert', '库存预警', 'in_app', 'stock_low',
     '库存预警: {{product_name}}',
     '产品 {{product_name}} ({{sku}}) 库存 {{current_qty}} 低于安全库存 {{safety_stock}}')
ON CONFLICT (code) DO NOTHING;
