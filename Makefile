.PHONY: dev dev-backend dev-frontend build stop clean db-reset db-restore lint test help

BACKEND_DIR := backend
FRONTEND_DIR := frontend

help: ## Show help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

dev: ## Start backend + frontend hot-reload
	@echo "Backend: http://localhost:8080 | Frontend: http://localhost:3002"
	@trap 'kill 0' EXIT; \
		(cd $(BACKEND_DIR) && uvicorn app.main:app --reload --port 8080 --host 0.0.0.0 2>&1 | sed 's/^/[backend] /') & \
		(cd $(FRONTEND_DIR) && npx vite --port 3002 2>&1 | sed 's/^/[frontend] /') & \
		wait

dev-backend: ## Start backend only
	cd $(BACKEND_DIR) && uvicorn app.main:app --reload --port 8080 --host 0.0.0.0

dev-frontend: ## Start frontend only
	cd $(FRONTEND_DIR) && npx vite --port 3002

build: ## Production build
	cd $(BACKEND_DIR) && pip install -r requirements.txt
	cd $(FRONTEND_DIR) && npm ci && npx vite build

stop: ## Stop all services
	-kill $$(lsof -t -i :8080) 2>/dev/null && echo "Backend stopped" || true
	-kill $$(lsof -t -i :3002) 2>/dev/null && echo "Frontend stopped" || true

clean: ## Clean build artifacts
	rm -rf $(BACKEND_DIR)/__pycache__ $(BACKEND_DIR)/app/**/__pycache__
	rm -rf $(FRONTEND_DIR)/dist

db-reset: ## Reset database
	@PGPASSWORD=aierp psql -h localhost -U aierp -d postgres -c "DROP DATABASE IF EXISTS aierp;"
	@PGPASSWORD=aierp psql -h localhost -U aierp -d postgres -c "CREATE DATABASE aierp OWNER aierp;"
	@echo "Database reset. Restart backend to run migrations."

db-restore: ## Restore from backup
	@PGPASSWORD=aierp pg_restore -h localhost -U aierp -d aierp -c ~/date/aierp_20260506_112657.dump
	@echo "Database restored from backup."

lint: ## Run linters
	cd $(BACKEND_DIR) && ruff check app/ && mypy app/ --ignore-missing-imports
	cd $(FRONTEND_DIR) && npx tsc --noEmit

test: ## Run tests
	cd $(BACKEND_DIR) && pytest -v
	cd $(FRONTEND_DIR) && npx vitest run
