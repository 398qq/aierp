-- 014 — RBAC seeds for commission scheme management (013 PRD)
--
-- Safe to run multiple times: all INSERTs use ON CONFLICT DO NOTHING.
--
-- Permissions matrix:
--   scheme.read     — 查看方案列表/详情            admin, finance_mgr, sales_mgr
--   scheme.create   — 创建方案                    admin, finance_mgr
--   scheme.update   — 编辑方案 (draft/pending)     admin, finance_mgr
--   scheme.activate — 激活/停用方案                admin, finance_mgr
--   scheme.delete   — 删除方案                    admin
--   scheme.simulate — 方案模拟 (what-if)           admin, finance_mgr, sales_mgr
--   scheme.assign   — 分配方案给用户/角色           admin, finance_mgr

-- ─────────────────────────────────────────────────────────────
-- 1. Insert commission_scheme permissions
-- ─────────────────────────────────────────────────────────────
INSERT INTO permissions (resource, action, name, description) VALUES
    ('commission_scheme', 'read', '查看提成方案', '查看方案列表和详情'),
    ('commission_scheme', 'create', '创建提成方案', '创建新方案'),
    ('commission_scheme', 'update', '编辑提成方案', '编辑已有方案'),
    ('commission_scheme', 'activate', '激活/停用方案', '改变方案状态'),
    ('commission_scheme', 'delete', '删除提成方案', '删除未引用方案'),
    ('commission_scheme', 'simulate', '方案模拟', 'What-if 方案推演'),
    ('commission_scheme', 'assign', '分配方案', '分配方案给用户/角色')
ON CONFLICT (resource, action) DO NOTHING;

-- ─────────────────────────────────────────────────────────────
-- 2. Grant to roles
-- ─────────────────────────────────────────────────────────────

-- admin gets all
INSERT INTO role_permissions (role_id, permission_id)
SELECT (SELECT id FROM roles WHERE name = 'admin'), id FROM permissions
WHERE resource = 'commission_scheme'
ON CONFLICT DO NOTHING;

-- sales/warehouse/finance roles — we need to create finance_mgr or use finance role
-- The existing 'finance' role gets read + simulate
INSERT INTO role_permissions (role_id, permission_id)
SELECT (SELECT id FROM roles WHERE name = 'finance'), id FROM permissions
WHERE (resource, action) IN (
    ('commission_scheme', 'read'),
    ('commission_scheme', 'simulate'),
    ('commission_scheme', 'create'),
    ('commission_scheme', 'update'),
    ('commission_scheme', 'activate'),
    ('commission_scheme', 'assign')
)
ON CONFLICT DO NOTHING;

-- sales role gets read only (view own scheme via /my-scheme)
INSERT INTO role_permissions (role_id, permission_id)
SELECT (SELECT id FROM roles WHERE name = 'sales'), id FROM permissions
WHERE (resource, action) = ('commission_scheme', 'read')
ON CONFLICT DO NOTHING;
