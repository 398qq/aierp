# AIERP — AI-Native ERP for Electronics Components Distribution

## Project Vision
An AI-driven ERP where every business entity (customers, products, opportunities) carries AI-generated insights. AI is not a feature — it's the connective tissue.

## Tech Stack
- **Backend**: Python 3.12 + FastAPI + SQLAlchemy 2.0 (async) + Alembic
- **Database**: PostgreSQL 16 + pgvector (embeddings)
- **AI**: SiliconFlow API (Qwen) + structured output + streaming
- **Frontend**: React 19 + TypeScript + Vite + Ant Design v5 + Recharts
- **State**: Zustand
- **Deploy**: Docker Compose

## Critical Commands
```bash
make dev          # Backend (uvicorn :8080) + Frontend (vite :3002)
make build        # Production build
make db-reset     # Drop and recreate database
make db-restore   # Restore from ~/date/ backup
make lint         # ruff + mypy + eslint
make test         # pytest + vitest
```

## Architecture — AI-Native Design
```
User → React UI → FastAPI → Service Layer → PostgreSQL
                        ↓
                   AI Service (SiliconFlow)
                   ├── Agents (Customer/Sales/Inventory)
                   ├── Embeddings (pgvector)
                   ├── Streaming (SSE)
                   └── Background Jobs (RFM, churn, predictions)
```

## Coding Standards
- **Pydantic v2** for all schemas — use `model_validate`, not `from_orm`
- **Async everywhere** — all DB calls and AI calls must be async
- **Type hints mandatory** — every function has return type annotation
- **Functions < 30 lines** — extract helper if longer
- **Error handling**: explicit try/except with context in service layer
- **API response format**: `{"code": 0, "msg": "success", "data": {...}}`
- **Pagination**: `{"list": [...], "total": N, "page": P, "page_size": S}`

## Naming Conventions
- **Files**: snake_case (`customer_service.py`)
- **Classes**: PascalCase (`CustomerService`)
- **Functions/Vars**: snake_case (`get_customer_by_id`)
- **API routes**: kebab-case in URL (`/api/v1/customer-analysis`)

## Security (Hard Rules)
- JWT with expiry, stored in HttpOnly cookie
- Passwords hashed with bcrypt
- ALL endpoints except /auth/* require JWT
- Never log credentials or tokens
- SQL injection prevention via parameterized queries (SQLAlchemy does this)

## Token Efficiency
- Don't re-read files just written
- Don't re-verify commands that succeeded
- Batch independent edits in parallel
- Don't summarize obvious results
