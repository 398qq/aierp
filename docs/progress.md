# Project Progress — AIERP

**Last Updated**: 2026-05-11
**Current Phase**: Phase 5 Complete (Approval + Procurement + Reports + RBAC)
**Latest Commit**: `6ad0b67` — feat: Phase 5 backend — RBAC, approval workflow, procurement AI, reports

---

## Working State

- **Branch**: master
- **Status**: Phase 5 complete — backend + frontend committed, polish in progress

---

## Phase 5 — B(审批工作流) + C(采购智能化) + D(报表与分析) + E(权限与安全) (COMPLETE)

### Backend (`6ad0b67`)
- [x] RBAC — 22 permissions, 4 roles, role-permission assignment, user-role binding (`permissions.py`, `rbac.py`)
- [x] Multi-level approval workflow — rules CRUD, submit/approve/reject, amount thresholds, audit trail (`approvals.py`, `approval.py`)
- [x] Procurement AI — restock suggestions, supplier recommendations, dashboard, PO calendar (`procurement.py`)
- [x] Reports — sales/AR/inventory/procurement predefined reports, CSV export, template CRUD (`reports.py`, `report.py`)
- [x] Audit logging — write_audit_log for all mutation endpoints (`permissions.py`)
- [x] Auto-seed RBAC data on startup (`database.py::_seed_rbac`)

### Frontend (this commit)
- [x] Roles & permissions management page (`system/Roles.tsx`)
- [x] Approval list with tabs + detail modal + approve/reject actions (`system/ApprovalList.tsx`)
- [x] Approval rules CRUD (`system/ApprovalRules.tsx`)
- [x] Audit log viewer with filters (`system/AuditLogList.tsx`)
- [x] Procurement dashboard — KPIs, restock suggestions, PO calendar (`procurement/ProcurementDashboard.tsx`)
- [x] Sales report with monthly orders/quotations + top products + CSV export (`reports/ReportSales.tsx`)
- [x] AR aging report with buckets + detail tables (`reports/ReportAR.tsx`)
- [x] Inventory report with stock levels + low stock/out of stock summary (`reports/ReportInventory.tsx`)
- [x] Procurement report with monthly trend + status summary (`reports/ReportProcurement.tsx`)
- [x] App.tsx — 10 new lazy-loaded routes
- [x] MainLayout.tsx — sidebar menu: 系统管理 (审批管理/审批规则/角色权限/审计日志), 采购智能, 报表分析 (4 reports)

### Tables Added
| Table | Purpose |
|-------|---------|
| `permissions` | 22 RBAC permissions (resource + action) |
| `roles` | 4 roles: admin, sales, warehouse, finance |
| `role_permissions` | Many-to-many role↔permission |
| `user_roles` | Many-to-many user↔role |
| `approval_rules` | Configurable approval rules by doc type |
| `approval_requests` | Submitted approval requests with multi-level flow |
| `approval_actions` | Individual approve/reject actions |
| `report_templates` | Saved report configurations |
| `audit_logs` | All mutation audit trail |

### New API Endpoints (12)
| Method | Path | Module |
|--------|------|--------|
| GET/POST/PUT/DELETE | `/permissions/roles` | RBAC |
| GET/PUT | `/permissions/users/{id}/roles` | RBAC |
| GET | `/permissions/audit-logs` | RBAC |
| GET/POST/PUT/DELETE | `/approvals/rules` | Approval |
| GET | `/approvals/requests` | Approval |
| POST | `/approvals/submit` | Approval |
| POST | `/approvals/requests/{id}/approve` | Approval |
| POST | `/approvals/requests/{id}/reject` | Approval |
| GET | `/ai/procurement/restock-suggest` | Procurement |
| GET | `/ai/procurement/supplier-recommend` | Procurement |
| GET | `/ai/procurement/dashboard` | Procurement |
| GET | `/ai/procurement/po-calendar` | Procurement |
| GET/POST/PUT/DELETE | `/reports/templates` | Reports |
| GET | `/reports/predefined/sales` | Reports |
| GET | `/reports/predefined/ar` | Reports |
| GET | `/reports/predefined/inventory` | Reports |
| GET | `/reports/predefined/procurement` | Reports |
| POST | `/reports/export/sales` | Reports |

---

## Phase 3 — AI Foundation + Embeddings (COMPLETE)

| Feature | Commit |
|---------|--------|
| Embedding pipeline with auto-embed + IVFFlat indexes | `3473048` |
| Customer360 dashboard, K-means segmentation | `3473048` |
| Watchtower anomaly scanner, demand forecasting | `3473048` |
| Streaming AI chat (SSE) | `5312f7d` |

---

## Phase 2 — Sales Core (COMPLETE)

| Feature | Commit |
|---------|--------|
| Full CRUD: opportunities, quotations, orders, delivery notes | `1324741` |
| Sales funnel kanban with drag-and-drop | `b5bf4e3` |
| Funnel stats, flow conversion, batch operations | `d7748bc` |
| Login page redesign | `163834e` |

---

## Phase 1 — Foundation (COMPLETE)

| Feature | Commit |
|---------|--------|
| Initial foundation | `a00f0ad` |

---

## Recent Milestones

| Commit | Description |
|--------|-------------|
| `8d23f6a` | fix: supplier对比模块 + AI服务路由 深度修复（Claude Code 10轮审查） |
| `8cfd095` | fix: SupplierCompare — 10 critical/medium bugs across frontend and backend |
| `c172120` | feat: add supplier delete endpoint + enhance supplier list |
| `b190769` | feat: pipeline kanban board + customer→supplier conversion |
| `834d272` | fix: deep audit round 2 — 11 critical/high bugs across 4 dimensions |
| `1af68c6` | fix: deep audit — 5 categories of bugs across backend and frontend |
| `c7a55c4` | fix: sales module — ORM relationships, schema fields, notification filter |
| `221eb96` | feat: add CLAUDE.md, brand-analysis-agent, brand-intel skill |
| `837561a` | fix: backend lint — E701/E712/F841/E501 |
| `b50b18e` | fix: Phase 4 SupplierCompare TypeError, rowKey collision, NaN guards |

---

## Known Issues / Technical Debt

| Issue | Severity | Status |
|-------|----------|--------|
| `.gitignore` excludes all `*.db` files — could miss legitimate DB files | Low | Monitor |

---

## Architecture Quick Reference

| Concern | Backend | Frontend |
|---------|---------|----------|
| RBAC | `core/permissions.py`, `api/v1/permissions.py`, `models/rbac.py` | `pages/system/Roles.tsx` |
| Audit Log | `core/permissions.py::write_audit_log`, `api/v1/permissions.py` | `pages/system/AuditLogList.tsx` |
| Approval | `api/v1/approvals.py`, `models/approval.py` | `pages/system/ApprovalList.tsx`, `pages/system/ApprovalRules.tsx` |
| Procurement AI | `api/v1/procurement.py` | `pages/procurement/ProcurementDashboard.tsx` |
| Reports | `api/v1/reports.py`, `models/report.py` | `pages/reports/Report{Sales,AR,Inventory,Procurement}.tsx` |
| Brand360 | `services/brand_intel_service.py` | `pages/brands/BrandDetail.tsx` |
| Supplier360 | `services/supplier_intel_service.py` | `pages/suppliers/SupplierDetail.tsx` |
| SupplierCompare | API in `api/v1/ai.py` | `pages/suppliers/SupplierCompare.tsx` |
| Product360 | `services/product_intel_service.py` | `pages/products/ProductDetail.tsx` |
| Global360 | `api/v1/dashboard.py` | `pages/dashboard/` |
| Watchtower | `services/watchtower_service.py` | `pages/dashboard/WatchtowerDashboard.tsx` |
| Embeddings | `services/embedding_pipeline.py` | N/A (backend-only) |
| AI Chat | API in `api/v1/ai.py` | `pages/ai/` |
| Sales AI | `services/sales_ai_pipeline.py` | `pages/sales/` |
