# Repository Guidelines

## Start here

Use this file as the short, repo-specific entry point. For deeper detail, follow the linked project docs instead of copying them into agent instructions.

- [docs/README.md](docs/README.md) — documentation index
- [docs/development-workflow.md](docs/development-workflow.md) — build, TDD, planning, review workflow
- [docs/architecture/README.md](docs/architecture/README.md) — architecture status and ADR pointers
- [docs/FRONTEND_HOOKS.md](docs/FRONTEND_HOOKS.md) — frontend hook refactor patterns
- [docs/FRONTEND_SECURITY.md](docs/FRONTEND_SECURITY.md) — frontend dependency/security posture
- [CLAUDE.md](CLAUDE.md) — repository-wide engineering bottom lines and command references

## Codebase map

- Backend: `backend/app/`
  - `api/` routes stay thin
  - `core/` security, middleware, request context
  - `models/` SQLAlchemy ORM
  - `schemas/` request/response contracts
  - `services/` domain logic and orchestration
  - `jobs/` scheduled work
  - `migrations/` SQL migration scripts
  - Tests live under `backend/tests/`
- Frontend: `frontend/src/`
  - `api/` is the single API layer
  - `components/` reusable UI
  - `layouts/` shell layout
  - `pages/` feature pages
  - `store/` Zustand state
  - `test/` frontend tests

## Working commands

Run from the repository root unless explicitly noted.

- `make dev` — run backend and frontend together
- `make dev-backend` / `make dev-frontend` — run one side only
- `make build` — install production dependencies and build the frontend bundle
- `make lint` — backend `ruff` + `mypy`, then frontend `tsc --noEmit`
- `make test` — backend pytest + frontend Vitest
- `make security-check` — backend `pip-audit` + frontend `npm audit`

## What agents should optimize for

1. Keep business logic in `services/` and routes thin.
2. Keep Pydantic schema contracts explicit at system boundaries.
3. Prefer `Decimal` for money and `Enum`/status transitions for ERP workflows.
4. Reuse existing repo patterns before introducing new abstractions.
5. Treat tests as part of the implementation, not an afterthought.

## Backend expectations

- Python 3.12, `snake_case` modules, `PascalCase` classes, `test_*.py` tests.
- Route handlers should parse input and delegate to services; they should not own business rules.
- Keep document totals, line items, and downstream statuses consistent.
- Use explicit timeouts and safe fallbacks for slow dependencies such as AI, OCR, logistics APIs, and payment integrations.
- Preserve soft-delete and request-context patterns.

## Frontend expectations

- TypeScript + React 19 + Vite + Ant Design.
- Use PascalCase for components/pages and camelCase for hooks/functions.
- Keep the API layer centralized in `frontend/src/api/index.ts`.
- Use dense, operational Ant Design screens rather than marketing-style layouts.
- Prefer existing shared UI primitives and keep feature-specific UI close to the page that owns it.

## Testing and validation

- Backend tests use `pytest` with `asyncio_mode = auto`.
- Mark database-heavy coverage with `@pytest.mark.integration` and lightweight cases with `@pytest.mark.unit` where appropriate.
- Frontend tests live under `frontend/src/test/` and should use `*.test.ts` / `*.test.tsx` names.
- When fixing timeouts, performance regressions, or integration issues, capture a clear before/after signal and explain the bounded slow path.

## PR and change hygiene

- Keep changes scoped and implementation-focused.
- Prefer concise, repo-relevant commit messages.
- When opening or reviewing a PR, mention the user-visible change, validation performed, and any migration/security/config impact.
- Do not commit secrets, environment files, or local credentials.

## Common pitfalls

- Do not add DB logic directly inside route handlers.
- Do not introduce new frontend API calls outside the centralized client layer.
- Do not use `float` for money or magic strings for ERP status transitions.
- Do not duplicate existing docs; link to them and keep this file minimal.
