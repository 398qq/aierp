.PHONY: dev dev-backend dev-frontend build stop clean db-reset db-backup db-restore lint test security-check help

BACKEND_DIR := backend
FRONTEND_DIR := frontend
BACKEND_PORT ?= 8080
UVICORN := $(shell test -x $(BACKEND_DIR)/.venv/bin/uvicorn && echo $(BACKEND_DIR)/.venv/bin/uvicorn || echo uvicorn)

help: ## Show help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

dev: ## Start backend + frontend hot-reload
	@echo "Backend: http://localhost:$(BACKEND_PORT) | Frontend: http://localhost:3002"
	@trap 'kill 0' EXIT; \
		(cd $(BACKEND_DIR) && ../$(UVICORN) app.main:app --reload --port $(BACKEND_PORT) --host 0.0.0.0 2>&1 | sed 's/^/[backend] /') & \
		(cd $(FRONTEND_DIR) && BACKEND_PORT=$(BACKEND_PORT) npx vite --port 3002 2>&1 | sed 's/^/[frontend] /') & \
		wait

dev-backend: ## Start backend only
	cd $(BACKEND_DIR) && ../$(UVICORN) app.main:app --reload --port $(BACKEND_PORT) --host 0.0.0.0

dev-frontend: ## Start frontend only
	cd $(FRONTEND_DIR) && BACKEND_PORT=$(BACKEND_PORT) npx vite --port 3002

build: ## Production build
	cd $(BACKEND_DIR) && pip install -r requirements.txt
	cd $(FRONTEND_DIR) && npm ci && npx vite build

stop: ## Stop all services
	-kill $$(lsof -t -i :$(BACKEND_PORT)) 2>/dev/null && echo "Backend stopped" || true
	-kill $$(lsof -t -i :3002) 2>/dev/null && echo "Frontend stopped" || true

clean: ## Clean build artifacts
	rm -rf $(BACKEND_DIR)/__pycache__ $(BACKEND_DIR)/app/**/__pycache__
	rm -rf $(FRONTEND_DIR)/dist

db-reset: ## Reset database
	@PGPASSWORD=aierp psql -h localhost -U aierp -d postgres -c "DROP DATABASE IF EXISTS aierp;"
	@PGPASSWORD=aierp psql -h localhost -U aierp -d postgres -c "CREATE DATABASE aierp OWNER aierp;"
	@echo "Database reset. Restart backend to run migrations."

db-backup: ## Backup database to ~/date/
	@mkdir -p ~/date
	@PGPASSWORD=aierp pg_dump -h localhost -U aierp -d aierp -F c -f ~/date/aierp_$$(date +%Y%m%d_%H%M%S).dump
	@echo "Database backed up to ~/date/"

db-restore: ## Restore from backup (BACKUP=~/date/aierp_YYYYMMDD_HHMMSS.dump)
	@PGPASSWORD=aierp pg_restore -h localhost -U aierp -d aierp -c $(BACKUP)
	@echo "Database restored."

lint: ## Run linters
	cd $(BACKEND_DIR) && ruff check app/ && mypy app/ --explicit-package-bases --ignore-missing-imports --exclude "app/api/v1/(permissions|finance|sales).py"
	cd $(FRONTEND_DIR) && npx tsc --noEmit

test: test-backend test-frontend ## Run all tests

test-backend: ## Run backend tests
	cd $(BACKEND_DIR) && pytest -v

test-backend-cov: ## Run backend tests with coverage
	cd $(BACKEND_DIR) && pytest -v --cov=app --cov-report=term-missing --cov-report=html

test-frontend: ## Run frontend tests
	cd $(FRONTEND_DIR) && npx vitest run

test-frontend-cov: ## Run frontend tests with coverage
	cd $(FRONTEND_DIR) && npx vitest run --coverage

security-check: ## Run dependency vulnerability checks
	cd $(BACKEND_DIR) && pip-audit -r requirements.txt
	cd $(FRONTEND_DIR) && npm audit --audit-level=high
