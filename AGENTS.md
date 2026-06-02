# Repository Guidelines

## Project Structure & Module Organization

This repo is split into a Python backend and a React frontend. Backend code lives in `backend/app/`: API routes in `api/`, middleware/security helpers in `core/`, SQLAlchemy models in `models/`, Pydantic schemas in `schemas/`, business logic in `services/`, scheduled work in `jobs/`, and SQL migrations in `migrations/`. Backend tests are in `backend/tests/`.

Frontend code lives in `frontend/src/`: API clients in `api/`, reusable UI in `components/`, layouts in `layouts/`, feature pages in `pages/`, shared state in `store/`, and tests in `test/`. Static PWA assets are in `frontend/public/`. Planning and requirements documents are under `docs/`.

## Build, Test, and Development Commands

Run commands from the repository root unless noted.

- `make dev`: start FastAPI with reload on `localhost:8080` and Vite on `localhost:3002`.
- `make dev-backend` / `make dev-frontend`: run only one side of the stack.
- `make build`: install production dependencies and build the Vite app.
- `make lint`: run backend `ruff` plus `mypy`, then frontend `tsc --noEmit`.
- `make test`: run backend pytest and frontend Vitest.
- `make security-check`: run `pip-audit` and high-severity `npm audit`.

## Coding Style & Naming Conventions

Backend targets Python 3.12. Use snake_case modules, PascalCase classes, and `test_*.py` tests. Place domain behavior in `services/`; keep route handlers thin and schema-driven. Use Ruff and mypy, respecting incremental ignores in `backend/mypy.ini`.

Frontend uses TypeScript, React 19, Vite, and Ant Design. Use PascalCase for components/pages, camelCase for functions/hooks, and the `@/*` alias for `frontend/src/*`. Keep feature-specific UI near its page unless reusable.

## Testing Guidelines

Backend tests use pytest with `asyncio_mode = auto`; mark database-dependent tests with `@pytest.mark.integration` and unit tests with `@pytest.mark.unit` where useful. Coverage: `make test-backend-cov`.

Frontend tests use Vitest and Testing Library in `frontend/src/test/`; name files `*.test.ts` or `*.test.tsx`. Coverage: `make test-frontend-cov`.

## Commit & Pull Request Guidelines

Git history uses concise imperative summaries, often Conventional Commit prefixes such as `feat:`, `fix:`, and `chore:`; Chinese summaries are common. Keep commits scoped, e.g. `fix: 兼容品牌分页返回`.

Pull requests should describe the user-visible change, list validation performed (`make test`, targeted pytest/Vitest commands), link issues or docs, and include screenshots for UI changes. Note migrations, environment changes, or security-sensitive configuration.

## Security & Configuration Tips

Backend environment examples are in `backend/.env.example` and test defaults in `backend/.env.test`. Do not commit real secrets from `backend/.env`. Database reset/backup helpers in the Makefile assume local PostgreSQL credentials; verify targets before running them.

## ERP Product Standards

When implementing ERP features, prioritize operational correctness over visual novelty. Treat each change as part of a business workflow with status transitions, permissions, auditability, reporting impact, and data consistency.

Core flows:

- inquiry → opportunity → quotation → sales order → delivery note → invoice → payment
- restock suggestion → purchase order → receiving → inventory ledger
- customer/supplier/product master data → transactional documents → reports

Backend expectations:

- Keep route handlers thin and put domain behavior in `services/`.
- Validate request/response contracts with schemas.
- Keep document totals, line items, and downstream statuses consistent.
- Bound slow dependencies such as AI, OCR, logistics APIs, payment gateways, and imports with explicit timeouts and safe fallback behavior.
- Consider RBAC, approval rules, audit logs, soft delete, request IDs, and slow-query logging for core workflows.

Frontend expectations:

- Build dense, scan-friendly Ant Design operational screens with tables, filters, batch actions, detail pages, status tags, and clear async/error states.
- Avoid marketing-style layouts for ERP modules.
- Keep UI copy business-facing and compact.

Validation expectations:

- Add targeted tests around status transitions, document conversions, totals, permissions, and slow/failing dependencies.
- For timeout or performance fixes, capture before/after timings and state the bounded slow path.
