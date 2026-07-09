-- 013 — 提成方案配置（Commission Scheme Config）
-- 注意：如果已有 commissions 表，本迁移作为增量；否则先建 commissions 再建 scheme 表。

-- ─────────────────────────────────────────────────────────────
-- 1. 提成方案主表
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS commission_schemes (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    version_no INT NOT NULL DEFAULT 1,
    status VARCHAR(20) NOT NULL DEFAULT 'draft'
        CHECK (status IN ('draft', 'pending', 'active', 'expired', 'inactive')),
    effective_from DATE NOT NULL DEFAULT CURRENT_DATE,
    effective_to DATE,
    is_default BOOLEAN NOT NULL DEFAULT FALSE,
    created_by BIGINT REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_schemes_status ON commission_schemes(status) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_schemes_effective ON commission_schemes(effective_from, effective_to) WHERE deleted_at IS NULL;

-- ─────────────────────────────────────────────────────────────
-- 2. 阶梯定义
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS scheme_tiers (
    id BIGSERIAL PRIMARY KEY,
    scheme_id BIGINT NOT NULL REFERENCES commission_schemes(id) ON DELETE CASCADE,
    tier_no INT NOT NULL,
    metric_type VARCHAR(20) NOT NULL DEFAULT 'monthly_sales'
        CHECK (metric_type IN ('monthly_sales', 'quarterly_sales', 'single_order', 'fixed_rate')),
    low_amount NUMERIC(18, 4) NOT NULL DEFAULT 0,
    high_amount NUMERIC(18, 4),
    rate NUMERIC(8, 4) NOT NULL CHECK (rate >= 0 AND rate <= 1),
    cap_amount NUMERIC(18, 4) NOT NULL DEFAULT 0,
    floor_amount NUMERIC(18, 4) NOT NULL DEFAULT 0,
    product_category VARCHAR(100),
    customer_level VARCHAR(20),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,

    CONSTRAINT ck_tier_range CHECK (low_amount >= 0 AND (high_amount IS NULL OR high_amount > low_amount)),
    CONSTRAINT ck_tier_cap_floor CHECK (floor_amount <= cap_amount OR cap_amount = 0)
);

CREATE INDEX IF NOT EXISTS idx_tiers_scheme ON scheme_tiers(scheme_id) WHERE deleted_at IS NULL;

-- ─────────────────────────────────────────────────────────────
-- 3. 方案分配
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS scheme_assignments (
    id BIGSERIAL PRIMARY KEY,
    scheme_id BIGINT NOT NULL REFERENCES commission_schemes(id) ON DELETE CASCADE,
    assignee_type VARCHAR(10) NOT NULL CHECK (assignee_type IN ('user', 'role')),
    assignee_id INT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,

    UNIQUE (assignee_type, assignee_id, deleted_at)
);

CREATE INDEX IF NOT EXISTS idx_assignments_scheme ON scheme_assignments(scheme_id) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_assignments_assignee ON scheme_assignments(assignee_type, assignee_id) WHERE deleted_at IS NULL;

-- ─────────────────────────────────────────────────────────────
-- 4. 方案版本审计
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS scheme_versions (
    id BIGSERIAL PRIMARY KEY,
    scheme_id BIGINT NOT NULL REFERENCES commission_schemes(id) ON DELETE CASCADE,
    version_no INT NOT NULL,
    snapshot JSONB NOT NULL,
    changed_by INT NOT NULL REFERENCES users(id),
    changed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_scheme_versions ON scheme_versions(scheme_id, version_no DESC);

-- ─────────────────────────────────────────────────────────────
-- 5. Commission 表增加 scheme_snapshot 字段
-- ─────────────────────────────────────────────────────────────
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'commissions') THEN
        BEGIN
            ALTER TABLE commissions ADD COLUMN scheme_snapshot JSONB;
        EXCEPTION
            WHEN duplicate_column THEN NULL;
        END;
    END IF;
END $$;
