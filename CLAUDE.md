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
| Frontend | React 19, TypeScript 5.7, Vite 6, Ant Design 5, Zustand 5, Recharts |
| Scheduler | APScheduler (background jobs in-process) |
| PDF | ReportLab (quotation PDF generation) |

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

# Linting
make lint                # Backend: ruff + mypy, Frontend: tsc --noEmit

# Database
make db-reset            # Drop and recreate PostgreSQL database
make db-backup           # pg_dump to ~/date/
make db-restore BACKUP=~/date/aierp_YYYYMMDD_HHMMSS.dump

# Docker
docker compose up -d     # Start pgvector + redis
```

## Architecture

### Backend (`backend/`)

```
backend/app/
├── main.py              # FastAPI app, lifespan, CORS
├── config.py            # Pydantic Settings — all config from env
├── database.py          # Async engine, session, Base, pgvector init
├── core/security.py     # JWT (jose) + bcrypt password hashing
├── api/
│   ├── deps.py          # get_current_user dependency (Bearer token → user dict)
│   └── v1/
│       ├── router.py    # Master router — all sub-routers under /api/v1
│       ├── auth.py      # POST /auth/login, GET /auth/me
│       ├── customers.py # CRUD + tags, contacts, follow-ups, alerts, import/export
│       ├── products.py  # Products, brands, suppliers, warehouses, inventory
│       ├── sales.py     # Opportunities, quotations, orders, deliveries, pipeline
│       ├── finance.py   # Invoices, payments, contracts, targets
│       ├── transactions.py # Purchase orders, tickets, visits, samples
│       ├── ai.py        # All /ai/* endpoints (intelligence, chat, agents)
│       ├── dashboard.py # Sales dashboard, watchtower, daily report
│       ├── public.py    # Unauthenticated inquiry portal
│       ├── notifications.py
│       ├── users.py
│       └── inventory_transactions.py
├── models/              # SQLAlchemy ORM models (all use Base from database.py)
│   ├── base.py          # TimestampMixin: id, created_at, updated_at, deleted_at
│   ├── customer.py      # Customer, Contact, FollowUp, Tag, AlertRule, etc.
│   ├── product.py       # Product, Brand, Supplier, Warehouse, Inventory
│   ├── sales.py         # Opportunity, Quotation, SalesOrder, DeliveryNote, Inquiry
│   ├── transaction.py   # PurchaseOrder, Ticket, Visit, Sample
│   ├── finance.py       # Invoice, Payment, Contract, SalesTarget, Notification
│   └── user.py          # User (role-based: admin/sales/warehouse/finance)
├── services/
│   ├── ai/              # AI client + agents
│   │   ├── client.py    # AIClient singleton (chat, chat_stream, chat_structured, embed)
│   │   ├── agents.py    # Agent classes: CustomerAgent, ProductAgent, InventoryAgent, etc.
│   │   ├── prompts.py   # Prompt templates
│   │   └── recommend.py # Recommendation logic
│   ├── sales_service.py      # Business logic for sales pipeline
│   ├── sales_ai_service.py   # AI enrichment for opportunities/quotations
│   ├── sales_ai_pipeline.py  # Pipeline kanban AI features
│   ├── brand_intel_service.py
│   ├── supplier_intel_service.py
│   ├── watchtower_service.py  # Cross-domain anomaly detection
│   ├── notification_service.py
│   ├── matching_service.py    # Product-customer matching
│   ├── embedding_pipeline.py
│   ├── pricing_service.py
│   └── pdf_service.py         # Quotation PDF generation
├── jobs/scheduler.py    # APScheduler: 9 background jobs (insights, embeddings, reports, cleanup)
└── migrations/          # Raw SQL migrations (pgvector extension, indexes)
```

### Frontend (`frontend/src/`)

```
frontend/src/
├── App.tsx              # Routes, lazy-loaded pages, auth guard
├── api/index.ts         # All API calls — axios-based, typed request/response
├── api/client.ts        # Axios instance with Bearer token interceptor
├── store/auth.ts        # Zustand auth store (token, login, logout)
├── layouts/MainLayout.tsx  # Ant Design ProLayout with sidebar
├── types/index.ts       # TypeScript interfaces for all entities
├── pages/
│   ├── dashboard/       # Watchtower, Global360
│   ├── customers/       # List, Detail, Form, Dashboard, 360, FollowUps
│   ├── products/        # List, Detail, PriceImport, InventoryManage
│   ├── suppliers/       # List, Detail, Dashboard, 360, Compare
│   ├── brands/          # List, Detail
│   ├── sales/           # Opportunities, Quotations, Orders, Deliveries, Invoices, Payments, Contracts, Targets, PurchaseOrders
│   ├── warehouse/       # Warehouses, Inventory Ledger
│   ├── tickets/         # List, Form, Detail
│   ├── inventory/       # Inventory list
│   ├── ai/Chat.tsx      # AI chat (SSE streaming)
│   ├── auth/Login.tsx
│   ├── public/InquiryPortal.tsx  # Public inquiry form
│   └── system/          # User management
└── components/
    ├── ai/AIInsight.tsx
    └── sales/           # PipelineBoard, OpportunityCard, SalesAIInsight
```

### Data Flow

```
Frontend (Ant Design) → axios → FastAPI /api/v1/* → Service Layer → SQLAlchemy → PostgreSQL
                                                      ↕
                                              AIClient → SiliconFlow API
                                              EmbeddingService → pgvector
                                              APScheduler → periodic background jobs
```

### Key Patterns

- **Soft delete**: All models inherit `TimestampMixin` with `deleted_at`. Queries always filter `deleted_at.is_(None)`.
- **AI calls**: `ai_client.chat()` for text, `ai_client.chat_structured(schema)` for JSON, `ai_client.embed()` for vectors. Tenacity retry (3 attempts, exponential backoff).
- **Embeddings**: Customers, Products, Suppliers, and Brand entities have pgvector `Vector(1024)` columns for semantic search.
- **Tests**: Backend uses `httpx.AsyncClient` with FastAPI dependency overrides. SQLite (aiosqlite) replaces PostgreSQL in tests; pgvector Vector columns are patched to Text for SQLite compatibility.
- **Auth**: JWT Bearer token. `get_current_user` dependency extracts `{user_id, username}` from token payload.
- **Env**: `backend/.env` (optional, overrides defaults in config.py). Test DB config via `TEST_DATABASE_URL` env var.

### Frontend Conventions

- All pages are lazy-loaded via `React.lazy()` in App.tsx
- `api/index.ts` is the single API layer — all endpoints defined here
- API responses: `{ code: 0, message: "ok", data: T }` pattern
- Zustand store for auth state only; page state is local `useState`/`useEffect`
- Ant Design 5 with Chinese locale (zhCN)
- Vite proxy: `/api` → `localhost:8080`

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
