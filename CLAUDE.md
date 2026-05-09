# AIERP — AI-Native ERP for Electronics Components Distribution

> **Owner**: Robin — 电子元器件分销商（IC 主动件为主）
> **Project Path**: `/home/ttdiy/aierp`

---

## Project Vision

An AI-driven ERP where every business entity (customers, products, opportunities) carries AI-generated insights. AI is not a feature — it's the connective tissue. The system combines ERP operations with vector embeddings, LLM reasoning, and streaming AI agents to assist a semiconductor distributor in managing brands, suppliers, inventory, and sales.

---

## Business Domain

### Core Entities & Relationships

```
Supplier (原厂/供应商)
  └── Brand (代理品牌线)  ← supplier_id FK
        └── Product (产品)
              └── Inventory (库存) / SalesOrderItem / QuotationItem

Customer (客户)
  ├── 终端 (end-customer, priority 1)
  ├── 贸易商 (trader, priority 2)
  ├── 方案商 (solution provider)
  ├── OEM/代工厂 (OEM/EMS, priority 3, on-demand)
  └── CustomerType: 终端 / 贸易商 / 方案商 / OEM

Opportunity (商机) → Quotation (报价) → SalesOrder (销售订单) → DeliveryNote (交货单)
```

**Key fields**:
- Customer: `level` (A/B/C/D), `lifecycle` (new/prospecting/active/dormant/churned), `customer_type` (终端/贸易商/方案商/OEM)
- Brand: `brand_type` (agency/own_brand/oem), `level` (A/B/C), `supplier_id` FK, `risk_level`, `authorization_status`
- Product: `brand_id` FK, `sku`, `category`, `package_type`
- Inventory: `product_id` + `warehouse_id`, `quantity`, `safety_stock`

### User Priority Preference

| Priority | Customer Type | 说明 |
|----------|--------------|------|
| 1 | 终端 (End-customer) | 优先服务，稳定需求 |
| 2 | 贸易商 (Trader) | 次之，配合拿货 |
| 3 | 代工厂 (OEM/EMS) | 按需配合，不主动拓展 |

### Key Industries (Target Markets)

- **工业无人机** (Industrial UAV/Drones)
- **GNSS 导航** (GNSS Navigation)
- **电子制造** (Electronics Manufacturing)

### 25 Agent Brand Lines (代理品牌线)

Brands are stored in DB (`brands` table, `brand_type = 'agency'`). Key categories include:

| Category | Example Brands (参考) |
|----------|---------------------|
| 安全加密 (Security/Crypto) | 瑞纳捷 RunJet, 为开微 WK, 银泰克 YinTec |
| 电源管理 (Power Management) | 力芯微 ETEK, 谷泰微 GTIC, 圣邦微 SGMicro |
| 音频视频 (Audio/Video) | 光华芯 CJC |
| 接口连接 (Interface/Connectivity) | 沁恒 CH, 和芯润德 CoreChip |
| 功率器件 (Power Devices) | 成都动信微 DX |
| MCU/SoC | 芯域 TH, 云岑微 YC |
| 模拟芯片 (Analog) | 上海广芯 Broadchip |

> Note: Full 25-brand list is in the database. Use the brands page UI or API to query.

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| **Backend** | Python 3.12 + FastAPI + SQLAlchemy 2.0 (async) + Alembic |
| **Database** | PostgreSQL 16 + pgvector (Vector(1024) embeddings) |
| **AI** | SiliconFlow API (Qwen model) + structured output + SSE streaming |
| **Frontend** | React 19 + TypeScript + Vite + Ant Design v5 + Recharts |
| **State** | Zustand |
| **Auth** | JWT (HttpOnly cookie), bcrypt |
| **Testing** | pytest (backend), vitest (frontend) |
| **Deploy** | Docker Compose |

### AI Architecture

```
User → React UI → FastAPI → Service Layer → PostgreSQL/pgvector
                              ↓
                         AI Service (SiliconFlow)
                         ├── Agents (Customer/Sales/Inventory/Brand)
                         ├── Embeddings (pgvector IVFFlat)
                         ├── Streaming (SSE)
                         └── Background Jobs (RFM, churn, demand forecast)
```

---

## Phase Evolution

### Phase 1 — Foundation (commit: `a00f0ad` wip)
- Basic work-in-progress foundation

### Phase 2 — Sales Core (commit: `d7748bc` + `1324741`)
- Full CRUD for opportunities, quotations, sales orders, delivery notes
- Sales funnel kanban board with drag-and-drop
- Funnel stats, flow conversion, batch operations
- Auto number generation, Excel export
- Login page redesign

### Phase 3 — AI Foundation + Embeddings (commit: `3473048`)
- **Embeddings**: Supplier/product vector support, `EmbeddingPipeline` with auto-embed, IVFFlat indexes, 24h refresh job
- **Customer Intelligence**: Customer360 dashboard, K-means segmentation, similar customers, semantic search
- **Predictive Analytics**: Watchtower anomaly scanner, demand forecasting (seasonality + trend + lead time), insight cache
- **Streaming Chat**: AI chat with conversation history (SSE)

### Phase 4 — Intelligence Platforms (commit: `78a4495`)
- **Brand360**: Brand profile, portfolio, health, risk, supplier matrix, lifecycle, price trends
- **Supplier360**: Supplier scorecard, delay prediction, alternatives, price variance, negotiation support
- **SupplierCompare**: Side-by-side supplier comparison
- **Product360**: Product intelligence with cross-sell recommendations
- **Global360**: Cross-domain aggregated view on main dashboard
- **WatchtowerDashboard**: Operational monitoring dashboard
- **Inventory Forecasting**: Demand forecast table on inventory page

---

## Code Organization

### Backend (`backend/`)
```
backend/
├── app/
│   ├── main.py              # FastAPI app entry, startup events
│   ├── config.py            # Settings (DB URL, AI API key, etc.)
│   ├── database.py          # AsyncEngine, session factory, Base
│   ├── api/
│   │   └── v1/
│   │       ├── router.py    # API v1 router aggregation
│   │       ├── deps.py      # JWT dependency, get_db, get_current_user
│   │       ├── auth.py      # /auth/* routes
│   │       ├── customers.py # /customers/* routes
│   │       ├── products.py  # /products/*, /brands/*, /suppliers/*
│   │       ├── sales.py     # /sales/* (opportunities, quotations, orders, delivery)
│   │       ├── dashboard.py # /dashboard/*
│   │       ├── ai.py        # /ai/* (all intelligence & streaming routes)
│   │       ├── finance.py   # /finance/*
│   │       ├── notifications.py
│   │       └── targets.py
│   ├── models/
│   │   ├── base.py          # TimestampMixin
│   │   ├── customer.py      # Customer, CustomerContact, CustomerFollowUp, AlertRule, etc.
│   │   ├── product.py       # Brand, Product, Supplier, Warehouse, Inventory, SupplierProduct
│   │   ├── sales.py         # Opportunity, Quotation, QuotationItem, SalesOrder, DeliveryNote
│   │   ├── finance.py       # Invoice, PaymentRecord, etc.
│   │   ├── transaction.py   # InventoryTransaction
│   │   └── user.py
│   ├── schemas/             # Pydantic v2 schemas (request/response)
│   ├── services/
│   │   ├── ai/
│   │   │   ├── client.py   # SiliconFlow API client
│   │   │   ├── agents.py   # Customer/Sales/Inventory agents
│   │   │   ├── prompts.py  # LLM prompts
│   │   │   └── recommend.py
│   │   ├── brand_intel_service.py      # Brand360 intelligence
│   │   ├── supplier_intel_service.py   # Supplier360 intelligence
│   │   ├── product_intel_service.py    # Product360 intelligence
│   │   ├── customer_service.py
│   │   ├── sales_service.py
│   │   ├── sales_ai_service.py         # Opportunity scoring, quotation optimization
│   │   ├── sales_ai_pipeline.py        # AI pipeline orchestration
│   │   ├── embedding_pipeline.py       # Auto-embed pipeline
│   │   ├── inventory_service.py
│   │   ├── watchtower_service.py       # Watchtower anomaly detection
│   │   ├── matching_service.py         # Customer-product matching
│   │   ├── nlp_query_service.py        # Natural language query
│   │   └── orchestration_service.py
│   └── jobs/
│       └── scheduler.py     # Background jobs (RFM, churn, embedding refresh)
├── alembic/                 # DB migrations
├── migrations/              # SQL migrations (005_brand_hub.sql, etc.)
├── scripts/                 # Utility scripts
├── tests/                  # pytest tests
└── requirements.txt
```

### Frontend (`frontend/src/`)
```
frontend/src/
├── App.tsx                 # Route definitions
├── api/
│   ├── client.ts           # Axios instance with interceptors
│   └── index.ts            # All API functions (typed)
├── layouts/
│   └── MainLayout.tsx      # Sidebar nav + header
├── pages/
│   ├── auth/LoginA.html, LoginB.html, LoginDesign.html  # Login page variants
│   ├── dashboard/          # Dashboard entry, Global360, WatchtowerDashboard
│   ├── customers/          # CustomerList, CustomerDetail, CustomerForm
│   ├── brands/             # BrandList, BrandDetail (with all Brand360 tabs)
│   ├── suppliers/          # SupplierList, SupplierDetail, Supplier360, SupplierCompare
│   ├── products/           # ProductList, ProductDetail, Product360
│   ├── inventory/          # Inventory page with demand forecasting
│   ├── sales/              # SalesFunnel, OpportunityList, QuotationList, etc.
│   ├── ai/                 # AI chat page (SSE streaming)
│   ├── notifications/
│   ├── tickets/
│   ├── settings/
│   └── users/
├── types/
│   └── index.ts            # All TypeScript interfaces (1100+ lines)
├── stores/                 # Zustand stores
└── components/
```

---

## API Conventions

### Response Format
```json
// Success
{ "code": 0, "msg": "success", "data": {...} }

// Paginated
{ "code": 0, "msg": "success", "data": { "list": [...], "total": N, "page": P, "page_size": S } }

// Error
{ "code": 400, "msg": "error description", "data": null }
```

### Route Naming
- URL: kebab-case (`/api/v1/customer-analysis`, `/api/v1/brand-profile`)
- Internal: snake_case files, PascalCase classes, snake_case functions

---

## Coding Standards

| Rule | Standard |
|------|----------|
| Schemas | **Pydantic v2** — use `model_validate`, NOT `from_orm` |
| DB | **Async everywhere** — all SQLAlchemy calls are `async` |
| Types | **Type hints mandatory** — every function has return type annotation |
| Functions | **< 30 lines** — extract helper if longer |
| Error handling | `try/except` with context in service layer |
| Auth | JWT in HttpOnly cookie; all endpoints except `/auth/*` require it |

---

## Critical Commands

```bash
make dev              # Backend (uvicorn :8080) + Frontend (vite :3002) hot-reload
make dev-backend      # Backend only on :8080
make dev-frontend     # Frontend only on :3002
make build            # Production build (pip install + npm ci + vite build)
make stop             # Kill processes on :8080 and :3002
make clean            # Remove __pycache__ and dist

make db-reset         # DROP + CREATE aierp database (requires psql)
make db-restore       # pg_restore from ~/date/aierp_20260506_112657.dump

make lint             # ruff check + mypy + tsc --noEmit
make test             # pytest + vitest
make test-backend     # pytest -v (SQLite for tests)
make test-backend-cov # pytest + coverage report (HTML)
make test-frontend    # vitest run
```

**Ports**: Backend `:8080`, Frontend `:3002`

---

## Brand Analysis Workflow

Brand analysis is accessible from **BrandDetail page** (click any brand name):

1. **Profile tab** — AI-generated brand overview (capabilities, positioning, competitiveness)
2. **Portfolio tab** — Brand × product matrix, customer penetration
3. **Health tab** — Revenue trend, margin analysis, customer concentration
4. **Risk tab** — Supplier risk, lifecycle risk, authorization risk, EOL risk
5. **Supplier Matrix tab** — Single-source products, supplier concentration risk
6. **Recommendations tab** — Alternative brands, cross-sell opportunities
7. **Compare button** — Side-by-side comparison with another brand

**Backend service**: `brand_intel_service.py` — `assess_brand_risk()`, `recommend_brands()`, `get_brand_profile()`

---

## Supplier Analysis Workflow

Supplier analysis is accessible from **SupplierDetail page**:

1. **360 view** — Full intelligence dashboard (Supplier360.tsx)
2. **Compare** — Side-by-side SupplierCompare.tsx
3. **AI routes** (6 total):
   - `GET /ai/supplier-scorecard`
   - `GET /ai/supplier-delay-prediction`
   - `GET /ai/supplier-alternatives`
   - `GET /ai/supplier-price-variance`
   - `GET /ai/supplier-360`
   - `GET /ai/supplier-negotiation`

**Backend service**: `supplier_intel_service.py`

---

## AI Service Overview

| Service | File | Key Functions |
|---------|------|---------------|
| Brand Intelligence | `brand_intel_service.py` | `assess_brand_risk()`, `recommend_brands()`, `get_brand_profile()` |
| Supplier Intelligence | `supplier_intel_service.py` | `get_scorecard()`, `predict_delay()`, `find_alternatives()` |
| Product Intelligence | `product_intel_service.py` | `get_product_360()`, `recommend_customers()` |
| Sales AI Pipeline | `sales_ai_pipeline.py` | `run_opportunity_scoring()`, `optimize_quotation()` |
| Watchtower | `watchtower_service.py` | Cross-domain anomaly detection |
| Embedding Pipeline | `embedding_pipeline.py` | Auto-embed on startup, 24h refresh |
| AI Client | `services/ai/client.py` | SiliconFlow API (Qwen), structured output, SSE |

---

## Security Rules (Enforced)

- JWT tokens stored in **HttpOnly cookie** (not localStorage)
- All endpoints **except `/auth/*`** require valid JWT
- Passwords hashed with **bcrypt**
- **Parameterized queries** — SQLAlchemy prevents SQL injection
- Never log credentials, tokens, or API keys
- `.env` for secrets (not committed to git)

---

## Token Efficiency

- Don't re-read files just written
- Don't re-verify commands that succeeded
- Batch independent edits in parallel
- Don't summarize obvious results
- Keep Claude Code turns focused and targeted

---

## Current Git Status

```
Branch: master (1 commit ahead of origin/master)
Working tree: clean
Last commit: 8d23f6a — fix: supplier对比模块 + AI服务路由 深度修复（Claude Code 10轮审查）
```

### Recent Commits

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

## Cross-Project Standards

See `~/.claude/CLAUDE.md` for:
- Commit message conventions
- Document naming (3-digit prefix, 9-chapter PRD structure)
- File naming standards
- Docs directory structure rules
- Universal coding standards
