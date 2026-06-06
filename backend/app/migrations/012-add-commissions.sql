-- Migration: 012-add-commissions.sql
-- Purpose: Sales commission tracking with state machine.
-- Date: 2026-06-05
-- Reversible: yes (DOWN at bottom)

BEGIN;

-- 1. Create table
CREATE TABLE IF NOT EXISTS commissions (
    id BIGSERIAL PRIMARY KEY,
    commission_no VARCHAR(64) UNIQUE,
    sales_order_id BIGINT NOT NULL REFERENCES sales_orders(id) ON DELETE RESTRICT,
    sales_user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    customer_id BIGINT REFERENCES customers(id) ON DELETE SET NULL,

    base_amount NUMERIC(20, 6) NOT NULL DEFAULT 0,
    rate NUMERIC(8, 4) NOT NULL DEFAULT 0,
    commission_amount NUMERIC(20, 6) NOT NULL DEFAULT 0,
    paid_amount NUMERIC(20, 6) NOT NULL DEFAULT 0,

    status VARCHAR(20) NOT NULL DEFAULT 'draft'
        CHECK (status IN ('draft', 'pending_approval', 'approved', 'paid', 'rejected', 'cancelled')),
    approved_by BIGINT REFERENCES users(id) ON DELETE SET NULL,
    approved_at TIMESTAMPTZ,
    paid_at TIMESTAMPTZ,
    period VARCHAR(20),
    notes TEXT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,
    created_by BIGINT REFERENCES users(id),
    updated_by BIGINT REFERENCES users(id),

    CONSTRAINT ck_commission_rate_range CHECK (rate >= 0 AND rate <= 1)
);

-- 2. Indexes (filter on soft-delete for partial indexes)
CREATE INDEX idx_commissions_sales_order_id ON commissions(sales_order_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_commissions_sales_user_id ON commissions(sales_user_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_commissions_status ON commissions(status) WHERE deleted_at IS NULL;
CREATE INDEX idx_commissions_period ON commissions(period) WHERE deleted_at IS NULL;
CREATE INDEX idx_commissions_created_at ON commissions(created_at DESC);

-- 3. Triggers (none — project uses SQLAlchemy onupdate=func.now() in TimestampMixin)

-- 4. RBAC seeds (resource/action name/description pattern matching 005-phase5-rbac.sql)
INSERT INTO permissions (resource, action, name, description) VALUES
    ('commissions', 'read',   '查看佣金',   '查看佣金列表和详情'),
    ('commissions', 'write',  '编辑佣金',   '创建和编辑佣金记录'),
    ('commissions', 'delete', '删除佣金',   '删除佣金记录'),
    ('commissions', 'approve','审批佣金',   '审批或驳回佣金'),
    ('commissions', 'pay',    '发放佣金',   '标记佣金已发放'),
    ('commissions', 'export', '导出佣金',   '导出佣金清单')
ON CONFLICT DO NOTHING;

COMMIT;

-- DOWN (commented; run manually if rolling back):
-- DROP TABLE IF EXISTS commissions;
-- DELETE FROM permissions WHERE code LIKE 'commission.%';
