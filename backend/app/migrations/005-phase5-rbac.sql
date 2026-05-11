-- Phase 5: RBAC + Approval + Report + Audit
-- 005-phase5-rbac.sql

-- Permissions
CREATE TABLE IF NOT EXISTS permissions (
    id SERIAL PRIMARY KEY,
    resource VARCHAR(50) NOT NULL,
    action VARCHAR(50) NOT NULL,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ,
    deleted_at TIMESTAMPTZ,
    UNIQUE(resource, action)
);

-- Roles
CREATE TABLE IF NOT EXISTS roles (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ,
    deleted_at TIMESTAMPTZ
);

-- Role-Permission links
CREATE TABLE IF NOT EXISTS role_permissions (
    role_id INT NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    permission_id INT NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
    PRIMARY KEY (role_id, permission_id)
);

-- User-Role links
CREATE TABLE IF NOT EXISTS user_roles (
    user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role_id INT NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    PRIMARY KEY (user_id, role_id)
);

-- Approval Rules
CREATE TABLE IF NOT EXISTS approval_rules (
    id SERIAL PRIMARY KEY,
    doc_type VARCHAR(50) NOT NULL,
    min_amount DECIMAL(15,2) DEFAULT 0,
    customer_level VARCHAR(20),
    flow_config JSONB NOT NULL DEFAULT '[]',
    enabled BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ,
    deleted_at TIMESTAMPTZ
);

-- Approval Requests
CREATE TABLE IF NOT EXISTS approval_requests (
    id SERIAL PRIMARY KEY,
    doc_type VARCHAR(50) NOT NULL,
    doc_id INT NOT NULL,
    submitter_id INT NOT NULL REFERENCES users(id),
    status VARCHAR(30) DEFAULT 'pending',
    current_level INT DEFAULT 1,
    flow_snapshot JSONB,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ,
    deleted_at TIMESTAMPTZ
);

-- Approval Actions
CREATE TABLE IF NOT EXISTS approval_actions (
    id SERIAL PRIMARY KEY,
    request_id INT NOT NULL REFERENCES approval_requests(id) ON DELETE CASCADE,
    approver_id INT NOT NULL REFERENCES users(id),
    action VARCHAR(20) NOT NULL,
    comment TEXT,
    level INT DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ,
    deleted_at TIMESTAMPTZ
);

-- Report Templates
CREATE TABLE IF NOT EXISTS report_templates (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    type VARCHAR(50) NOT NULL,
    config JSONB NOT NULL DEFAULT '{}',
    created_by INT REFERENCES users(id),
    is_public BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ,
    deleted_at TIMESTAMPTZ
);

-- Audit Logs
CREATE TABLE IF NOT EXISTS audit_logs (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id),
    username VARCHAR(100),
    action VARCHAR(50) NOT NULL,
    resource_type VARCHAR(50) NOT NULL,
    resource_id INT,
    summary TEXT,
    ip_address VARCHAR(50),
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Add columns to existing tables
ALTER TABLE purchase_orders ADD COLUMN IF NOT EXISTS approval_request_id INT;
ALTER TABLE quotations ADD COLUMN IF NOT EXISTS approval_request_id INT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT true;

-- Seed default permissions
INSERT INTO permissions (resource, action, name, description) VALUES
    ('customers', 'read', '查看客户', '查看客户列表和详情'),
    ('customers', 'write', '编辑客户', '创建和编辑客户信息'),
    ('customers', 'delete', '删除客户', '删除客户'),
    ('customers', 'export', '导出客户', '导出客户数据'),
    ('products', 'read', '查看产品', '查看产品列表和详情'),
    ('products', 'write', '编辑产品', '创建和编辑产品信息'),
    ('products', 'delete', '删除产品', '删除产品'),
    ('sales', 'read', '查看销售', '查看商机/报价/订单'),
    ('sales', 'write', '编辑销售', '创建和编辑销售单据'),
    ('sales', 'delete', '删除销售', '删除销售单据'),
    ('sales', 'approve', '审批销售', '审批报价和订单'),
    ('purchases', 'read', '查看采购', '查看采购订单'),
    ('purchases', 'write', '编辑采购', '创建和编辑采购订单'),
    ('purchases', 'approve', '审批采购', '审批采购订单'),
    ('finance', 'read', '查看财务', '查看发票/回款/合同'),
    ('finance', 'write', '编辑财务', '创建和编辑财务单据'),
    ('inventory', 'read', '查看库存', '查看库存和仓库'),
    ('inventory', 'write', '编辑库存', '调整库存'),
    ('reports', 'read', '查看报表', '查看和导出报表'),
    ('reports', 'write', '管理报表', '创建和管理报表模板'),
    ('system', 'read', '查看系统', '查看用户和角色'),
    ('system', 'write', '管理系统', '管理用户/角色/权限')
ON CONFLICT (resource, action) DO NOTHING;

-- Seed default roles
INSERT INTO roles (name, description) VALUES
    ('admin', '系统管理员 — 所有权限'),
    ('sales', '销售 — 客户/销售/商机管理'),
    ('warehouse', '仓库 — 产品/库存/采购管理'),
    ('finance', '财务 — 财务/报表管理')
ON CONFLICT (name) DO NOTHING;

-- Assign all permissions to admin role
INSERT INTO role_permissions (role_id, permission_id)
SELECT (SELECT id FROM roles WHERE name = 'admin'), id FROM permissions
ON CONFLICT DO NOTHING;

-- Assign permissions to sales role
INSERT INTO role_permissions (role_id, permission_id)
SELECT (SELECT id FROM roles WHERE name = 'sales'), id FROM permissions
WHERE (resource, action) IN (
    ('customers', 'read'), ('customers', 'write'), ('customers', 'export'),
    ('products', 'read'),
    ('sales', 'read'), ('sales', 'write'),
    ('reports', 'read')
)
ON CONFLICT DO NOTHING;

-- Assign permissions to warehouse role
INSERT INTO role_permissions (role_id, permission_id)
SELECT (SELECT id FROM roles WHERE name = 'warehouse'), id FROM permissions
WHERE (resource, action) IN (
    ('products', 'read'), ('products', 'write'),
    ('purchases', 'read'), ('purchases', 'write'),
    ('inventory', 'read'), ('inventory', 'write'),
    ('reports', 'read')
)
ON CONFLICT DO NOTHING;

-- Assign permissions to finance role
INSERT INTO role_permissions (role_id, permission_id)
SELECT (SELECT id FROM roles WHERE name = 'finance'), id FROM permissions
WHERE (resource, action) IN (
    ('customers', 'read'), ('sales', 'read'),
    ('finance', 'read'), ('finance', 'write'),
    ('reports', 'read'), ('reports', 'write')
)
ON CONFLICT DO NOTHING;

-- Assign admin role to existing admin user
INSERT INTO user_roles (user_id, role_id)
SELECT (SELECT id FROM users WHERE username = 'admin'), (SELECT id FROM roles WHERE name = 'admin')
ON CONFLICT DO NOTHING;
