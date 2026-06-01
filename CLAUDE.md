# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AIERP is an AI-powered ERP platform for small/medium electronics trading companies. It handles the full sales pipeline (opportunity → quotation → order → delivery → invoice → payment), plus procurement, inventory, customer/supplier management, and AI-driven intelligence features like RFM analysis, churn prediction, brand benchmarking, supplier scoring, demand forecasting, and inquiry auto-reply.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.12, FastAPI, SQLAlchemy 2.0 (async), Pydantic v2 |
| Database | PostgreSQL 16 + pgvector (vector embeddings) |
| Cache | Redis 7 |
| AI Provider | SiliconFlow API (OpenAI-compatible) — DeepSeek-V4-Flash for chat, BAAI/bge-large-zh-v1.5 for embeddings |
| Frontend | React 19.2, TypeScript 6.0, Vite 8, Ant Design 6, Zustand 5, Recharts |
| Scheduler | APScheduler (background jobs in-process) |
| PDF | ReportLab (quotation PDF), pytesseract/rapidocr (sales order PDF import) |

## Key Commands

```bash
# Development (hot-reload)
make dev                 # Start both backend :8080 and frontend :3002
make dev-backend         # Backend only
make dev-frontend        # Frontend only

# Testing
make test                # Run all tests (backend pytest + frontend vitest)
make test-backend        # pytest -v
make test-backend-cov    # pytest with coverage
make test-frontend       # vitest run
make test-frontend-cov   # vitest with coverage

# Single test
pytest backend/tests/path/to/test_file.py::test_name -v

# Linting
make lint                # Backend: ruff check + mypy, Frontend: tsc --noEmit

# Security
make security-check      # pip-audit backend + npm audit frontend

# Database
make db-reset            # Drop and recreate PostgreSQL database
make db-backup           # pg_dump to ~/date/
make db-restore BACKUP=~/date/aierp_YYYYMMDD_HHMMSS.dump

# Docker (start pgvector + redis)
docker compose up -d

# Build
make build               # pip install backend + vite build frontend
```

## Architecture

### Backend (`backend/`)

```
backend/app/
├── main.py              # FastAPI app, lifespan, CORS, health endpoints
├── config.py            # Pydantic Settings — all config from env
├── database.py          # Async engine, session, Base, pgvector init, slow-query logging
├── core/                # Security (JWT, bcrypt), error handlers, rate_limit, request_logging, request_context, security_headers
├── api/
│   ├── deps.py          # get_current_user (Bearer token + httpOnly cookie fallback → user dict with roles)
│   └── v1/
│       ├── router.py    # Master router — 25+ sub-routers under /api/v1
│       ├── auth.py      # POST /auth/login, GET /auth/me, change-password
│       ├── customers.py # CRUD + tags, contacts, follow-ups, alerts, import/export
│       ├── products.py  # Products, brands, suppliers, warehouses, inventory
│       ├── sales.py     # Opportunities, quotations, orders, deliveries, pipeline
│       ├── finance.py   # Invoices, payments, contracts
│       ├── transactions.py # Purchase orders, tickets, visits, samples, payments
│       ├── ai.py        # All /ai/* endpoints (intelligence, chat, agents)
│       ├── dashboard.py # Sales dashboard, watchtower, daily report
│       ├── public.py    # Unauthenticated inquiry portal
│       ├── approvals.py # Approval workflow engine
│       ├── documents.py # Document management
│       ├── export_import.py
│       ├── finance_accounts.py
│       ├── integrations.py
│       ├── notifications.py
│       ├── permissions.py # RBAC permission management
│       ├── procurement.py
│       ├── reports.py
│       ├── targets.py   # Separate from finance
│       ├── users.py
│       └── inventory_transactions.py
├── models/             # SQLAlchemy ORM models (soft-delete via TimestampMixin)
│   ├── base.py          # TimestampMixin: id, created_at, updated_at, deleted_at
│   ├── customer.py      # Customer, Contact, FollowUp, Tag, AlertRule, etc.
│   ├── product.py       # Product, Brand, Supplier, Warehouse, Inventory
│   ├── sales.py         # Opportunity, Quotation, SalesOrder, DeliveryNote, Inquiry
│   ├── transaction.py   # PurchaseOrder, Ticket, Visit, Sample
│   ├── finance.py       # Invoice, Payment, Contract, SalesTarget, Notification
│   ├── account.py       # Chart of accounts
│   ├── approval.py      # Approval workflow models
│   ├── document.py      # Document/attachment storage
│   ├── rbac.py          # Roles, permissions, user_role mapping
│   ├── report.py        # Saved reports
│   └── user.py          # User model
├── schemas/            # Pydantic request/response schemas (mirrors models/)
├── services/
│   ├── ai/              # AI client + agents
│   │   ├── client.py    # AIClient singleton: chat, chat_stream, chat_structured, embed (tenacity retry 3x)
│   │   ├── agents.py    # Agent classes: CustomerAgent, ProductAgent, InventoryAgent, WatchtowerService, etc.
│   │   ├── prompts.py   # Prompt templates
│   │   └── recommend.py # AI recommendation logic
│   ├── sales_service.py           # Business logic for sales pipeline
│   ├── sales_ai_service.py        # AI enrichment for opportunities/quotations
│   ├── sales_ai_pipeline.py       # Pipeline kanban AI features
│   ├── sales_order_pdf_import.py  # PDF → structured sales order extraction
│   ├── brand_intel_service.py
│   ├── supplier_intel_service.py
│   ├── po_intel_service.py        # Purchase order AI intelligence
│   ├── contract_intel_service.py
│   ├── finance_intel_service.py
│   ├── product_intel_service.py
│   ├── ticket_intel_service.py
│   ├── target_intel_service.py
│   ├── nlp_query_service.py       # Natural language → DB query
│   ├── watchtower_service.py      # Cross-domain anomaly detection
│   ├── notification_service.py
│   ├── matching_service.py        # Product-customer matching
│   ├── embedding_pipeline.py
│   ├── pricing_service.py
│   ├── pdf_service.py             # Quotation PDF generation (ReportLab)
│   ├── cache_service.py           # Redis caching layer
│   ├── docno.py                   # Document number generation
│   ├── finance_service.py
│   ├── inventory_service.py
│   ├── customer_service.py
│   ├── orchestration_service.py   # Cross-domain orchestration
│   └── pagination.py
├── jobs/scheduler.py    # APScheduler: 9 background jobs (6h/12h/24h intervals + cron at 18:00)
└── migrations/          # Raw SQL migrations (pgvector extension, RBAC seed data, indexes)
```

### Middleware Pipeline

Applied in `main.py` in this order:
1. **CORSMiddleware** — configured origins from env
2. **RateLimitMiddleware** — per-IP rate limiting
3. **RequestLoggingMiddleware** — logs method, path, status, duration
4. **SecurityHeadersMiddleware** — CSP, HSTS, X-Content-Type-Options, etc.
5. **RequestContextMiddleware** — request_id injection for tracing
6. **Exception handlers** — unified `{code, msg, data, request_id}` response format

### Frontend (`frontend/src/`)

```
frontend/src/
├── App.tsx              # Routes (react-router-dom v7), lazy-loaded pages, auth guard
├── api/index.ts         # All API calls — axios-based, typed request/response
├── api/client.ts        # Axios instance with httpOnly cookie auth interceptor + error normalization
├── store/auth.ts        # Zustand auth store (login, logout, user state)
├── layouts/MainLayout.tsx  # Ant Design ProLayout with sidebar
├── types/index.ts       # TypeScript interfaces for all entities + APIResponse<T> + PageData<T>
├── pages/               # One directory per domain — lazy-loaded
│   ├── ai/              # AI Chat (SSE streaming) + follow-up intelligence
│   ├── auth/            # Login page
│   ├── brands/          # List, Detail, Dashboard, 360, Compare
│   ├── customers/       # List, Detail, Form, Dashboard, 360, FollowUps, Recognition
│   ├── dashboard/       # Watchtower, Global360
│   ├── finance/         # Invoices, Payments
│   ├── import-export/   # Data import/export UI
│   ├── inventory/       # Inventory list, ledger
│   ├── notifications/   # Notification center
│   ├── procurement/     # Purchase orders, procurement planning
│   ├── products/        # List, Detail, PriceImport, InventoryManage, Associations
│   ├── public/          # InquiryPortal (unauthenticated)
│   ├── reports/         # Report generation
│   ├── sales/           # Opportunities, Quotations, Orders, Deliveries, Invoices, Payments, Contracts, Targets, PurchaseOrders, AI insights
│   ├── settings/        # System settings
│   ├── suppliers/       # List, Detail, Dashboard, 360, Compare
│   ├── system/          # User management
│   ├── tickets/         # List, Form, Detail, clusters
│   └── warehouse/       # Warehouses, Inventory Ledger
└── components/
    ├── ai/AIInsight.tsx  # Reusable AI insight card
    └── sales/            # PipelineBoard (dnd-kit), OpportunityCard, SalesAIInsight
```

### Data Flow

```
Frontend (Ant Design 6) → axios (withCredentials) → FastAPI /api/v1/* → Service Layer → SQLAlchemy 2.0 async → PostgreSQL
                                                         ↕                                                     ↕
                                                 AIClient → SiliconFlow API                          pgvector (Vector(1024))
                                                 EmbeddingService → pgvector                         Redis (caching)
                                                 APScheduler → 9 periodic jobs
```

### Key Patterns

- **Soft delete**: All models inherit `TimestampMixin` with `deleted_at`. Queries always filter `deleted_at.is_(None)`.
- **Auth**: JWT in httpOnly cookie (`aierp_token`) + Bearer token fallback. `get_current_user` dependency extracts `{user_id, username, roles}`.
- **RBAC**: Role-based access control. Users → roles → permissions. Permission checks via `require_permissions()` dependency.
- **AI calls**: `ai_client.chat()` for text, `ai_client.chat_stream()` for SSE, `ai_client.chat_structured(schema)` for JSON, `ai_client.embed()` for vectors. Tenacity retry (3 attempts, exponential backoff).
- **Embeddings**: Customers, Products, Suppliers, and Brand entities have pgvector `Vector(1024)` columns for semantic search.
- **AI Agents**: `services/ai/agents.py` defines domain-specific agents (CustomerAgent, ProductAgent, InventoryAgent, WatchtowerService, etc.) that combine AI calls with database operations.
- **Tests**: SQLite (aiosqlite) replaces PostgreSQL. pgvector Vector columns are patched to `Text` in conftest.py for SQLite compatibility. FastAPI dependency overrides + httpx.AsyncClient.
- **Error handling**: Unified `{code: number, msg: string, data: T, request_id?: string}` response format. Global exception handlers for HTTPException, RequestValidationError, and unhandled exceptions.
- **Health endpoints**: `GET /health` (db+redis+ai checks), `GET /health/ready` (db-only liveness), `GET /health/live` (always ok).
- **Scheduler**: 9 APScheduler jobs — sales insights refresh (6h), overdue alerts (12h), target progress (24h), contract expiry (24h), embedding refresh (24h), watchtower scan (4h), customer insights (24h), daily report (cron 18:00), notification cleanup (24h).
- **Config**: All config from environment via Pydantic Settings with `backend/.env` override. Key vars: `DB_HOST/PORT/USER/PASSWORD/NAME`, `JWT_SECRET`, `AI_API_KEY`, `AI_BASE_URL`, `CORS_ORIGINS`, `REDIS_URL`.
- **Slow query logging**: SQLAlchemy event listener logs queries exceeding `SLOW_QUERY_THRESHOLD_MS` with request_id and duration.

### Frontend Conventions

- All pages are lazy-loaded via `React.lazy()` in App.tsx
- `api/index.ts` is the single API layer — all typed endpoints defined here
- API response pattern: `{ code: 0, msg: "ok", data: T }` — error responses include `request_id` for tracing
- `api/client.ts`: axios instance with `withCredentials: true` (httpOnly cookie). Error interceptor normalizes messages (401 → redirect to /login, timeout → "请求超时")
- Zustand store for auth state only; page state is local `useState`/`useEffect`
- Ant Design 6 with Chinese locale (zhCN) and `@ant-design/v5-patch-for-react-19`
- Vite proxy: `/api` → `localhost:8080` (configurable via `BACKEND_PORT` env var)
- DnD (PipelineBoard): `@dnd-kit/core` + `@dnd-kit/sortable`
- Charts: Recharts for dashboards and analytics
- Excel import: `read-excel-file`
- AI Chat: SSE streaming via EventSource

## Rules

- Do what has been asked; nothing more, nothing less
- NEVER create files unless absolutely necessary — prefer editing existing files
- NEVER create documentation files unless explicitly requested
- ALWAYS read a file before editing it
- NEVER commit secrets, credentials, or .env files
- Keep files under 500 lines
- Validate input at system boundaries
- ALWAYS run tests after code changes: `make test`
- ALWAYS verify build succeeds before committing: `make lint`
