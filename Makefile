.PHONY: dev dev-backend dev-frontend build stop clean db-reset db-backup db-backup-remote db-backup-cron db-restore db-migrate db-revision lint test security-check help version bump-patch bump-minor bump-major release prod-start prod-stop prod-restart prod-status prod-logs health-check db-backup-list db-backup-clean db-shell deps-update deps-audit ops-alert ops-alert-cron docker-build docker-up docker-down docker-logs docker-ps

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

db-backup: ## Backup database to ~/date/ (uses scripts/backup-pg.sh, compressed + verified)
	./scripts/backup-pg.sh

db-backup-remote: ## Backup to local + remote (REMOTE_BACKUP_DIR=/path)
	REMOTE_BACKUP_DIR=$${REMOTE_BACKUP_DIR} ./scripts/backup-pg.sh

db-backup-cron: ## Show cron line to install backup nightly
	@echo "0 2 * * * /home/ttdiy/aierp/scripts/backup-pg.sh >> /home/ttdiy/aierp/logs/backup.log 2>&1"
	@echo ""
	@echo "To install: (crontab -l 2>/dev/null; cat <(echo '0 2 * * * /home/ttdiy/aierp/scripts/backup-pg.sh >> /home/ttdiy/aierp/logs/backup.log 2>&1')) | crontab -"

db-restore: ## Restore from backup (BACKUP=~/date/aierp_YYYYMMDD_HHMMSS.dump)
	@PGPASSWORD=aierp pg_restore -h localhost -U aierp -d aierp -c $(BACKUP)
	@echo "Database restored."

db-migrate: ## Run Alembic migrations to head
	@echo "Running Alembic migrations..."
	@cd backend && alembic upgrade head
	@echo "Migrations applied."

db-revision: ## Create new Alembic migration (MSG="your message")
	@cd backend && alembic revision --autogenerate -m "$(MSG)"

db-stamp: ## Stamp current DB as head (use after manual SQL migration)
	@cd backend && alembic stamp head

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

# ---------------------------------------------------------------------------
# Version bump & release
# ---------------------------------------------------------------------------
version: ## Show current version
	@grep -E 'VERSION.*:.*str' backend/app/config.py | grep -oE '[0-9]+\.[0-9]+\.[0-9]+'

bump-patch: ## Bump patch version (2.0.0 → 2.0.1)
	@./scripts/bump-version.sh patch

bump-minor: ## Bump minor version (2.0.0 → 2.1.0)
	@./scripts/bump-version.sh minor

bump-major: ## Bump major version (2.0.0 → 3.0.0)
	@./scripts/bump-version.sh major

release: build lint test ## Full release build (build + lint + test)
	@echo "All checks passed. Ready to bump version."
	@echo "Run: make bump-patch  (or bump-minor / bump-major)"

# ===========================================================================
# Production operations (Stage 6 Day 1)
# Use these after 'make build' to run the system in a server-like way
# (uvicorn workers, no reload, log to file).
# ===========================================================================
PROD_LOG_DIR ?= ./logs
PROD_PID_DIR ?= ./pids
PROD_WORKERS ?= 2

prod-start: ## Start backend in production mode (workers + no reload, logs to file)
	@mkdir -p $(PROD_LOG_DIR) $(PROD_PID_DIR)
	@if [ -f $(PROD_PID_DIR)/backend.pid ] && kill -0 $$(cat $(PROD_PID_DIR)/backend.pid) 2>/dev/null; then \
		echo "Backend already running (PID $$(cat $(PROD_PID_DIR)/backend.pid))"; \
	else \
		cd $(BACKEND_DIR) && nohup ../$(UVICORN) app.main:app \
			--host 0.0.0.0 --port $(BACKEND_PORT) \
			--workers $(PROD_WORKERS) --no-access-log \
			> $(PROD_LOG_DIR)/backend.log 2>&1 & \
		echo $$! > $(PROD_PID_DIR)/backend.pid; \
		sleep 2; \
		echo "Backend started (PID $$(cat $(PROD_PID_DIR)/backend.pid), workers=$(PROD_WORKERS))"; \
		echo "Logs: tail -f $(PROD_LOG_DIR)/backend.log"; \
	fi

prod-stop: ## Stop production backend
	@if [ -f $(PROD_PID_DIR)/backend.pid ]; then \
		PID=$$(cat $(PROD_PID_DIR)/backend.pid); \
		if kill -0 $$PID 2>/dev/null; then \
			kill $$PID; \
			sleep 2; \
			echo "Backend stopped (was PID $$PID)"; \
		else \
			echo "Backend PID $$PID not running"; \
		fi; \
		rm -f $(PROD_PID_DIR)/backend.pid; \
	else \
		kill $$(lsof -t -i :$(BACKEND_PORT)) 2>/dev/null && echo "Backend stopped" || echo "No backend running"; \
	fi

prod-restart: prod-stop prod-start ## Restart production backend

prod-status: ## Show production backend status
	@if [ -f $(PROD_PID_DIR)/backend.pid ] && kill -0 $$(cat $(PROD_PID_DIR)/backend.pid) 2>/dev/null; then \
		PID=$$(cat $(PROD_PID_DIR)/backend.pid); \
		echo "Backend RUNNING (PID $$PID)"; \
		echo "  Port:  $(BACKEND_PORT)"; \
		echo "  Workers: $(PROD_WORKERS)"; \
		echo "  Memory: $$(ps -p $$PID -o rss= 2>/dev/null | awk '{printf "%.1f MB", $$1/1024}')"; \
		echo "  CPU:    $$(ps -p $$PID -o %cpu= 2>/dev/null | xargs) %"; \
		echo "  Uptime: $$(ps -p $$PID -o etime= 2>/dev/null | xargs)"; \
	else \
		echo "Backend NOT running"; \
	fi

prod-logs: ## Tail production backend log (Ctrl+C to exit)
	@if [ -f $(PROD_LOG_DIR)/backend.log ]; then \
		tail -f $(PROD_LOG_DIR)/backend.log; \
	else \
		echo "No log file at $(PROD_LOG_DIR)/backend.log"; \
	fi

# ===========================================================================
# Health check + monitoring (Stage 6 Day 2)
# ===========================================================================
health-check: ## Health check (DB + Redis + disk + memory)
	@echo "=== AIERP Health Check ==="
	@echo ""
	@echo "1. Backend HTTP /health/live:"
	@curl -sf http://localhost:$(BACKEND_PORT)/health/live && echo "  ✅ UP" || echo "  ❌ DOWN"
	@echo ""
	@echo "2. PostgreSQL:"
	@PGPASSWORD=aierp psql -h localhost -U aierp -d aierp -c "SELECT '✅ UP' as status, version()" -t 2>&1 | head -2
	@echo ""
	@echo "3. Disk usage:"
	@df -h / | tail -1 | awk '{printf "  Used: %s / %s (%s)\n", $$3, $$2, $$5}'
	@echo ""
	@echo "4. Memory:"
	@free -h | grep Mem | awk '{printf "  Used: %s / %s\n", $$3, $$2}'
	@echo ""
	@echo "5. Backup freshness (latest):"
	@ls -1t ~/date/aierp_*.dump 2>/dev/null | head -1 | xargs -I{} ls -lh {} | awk '{printf "  %s %s %s\n", $$6, $$7, $$9}' || echo "  ❌ No backup found"

# ===========================================================================
# Backup management (Stage 6 Day 3)
# ===========================================================================
BACKUP_DIR ?= ~/date
BACKUP_KEEP_DAYS ?= 7

db-backup-list: ## List all database backups
	@echo "=== Database Backups (in $(BACKUP_DIR)) ==="
	@ls -lht $(BACKUP_DIR)/aierp_*.dump 2>/dev/null | head -20 || echo "No backups found"
	@echo ""
	@echo "Total size:"
	@du -sh $(BACKUP_DIR) 2>/dev/null || echo "0"

db-backup-clean: ## Delete backups older than $(BACKUP_KEEP_DAYS) days
	@echo "Cleaning backups older than $(BACKUP_KEEP_DAYS) days..."
	@find $(BACKUP_DIR) -name "aierp_*.dump" -mtime +$(BACKUP_KEEP_DAYS) -print -delete
	@find $(BACKUP_DIR) -name "aierp_*.sql" -mtime +$(BACKUP_KEEP_DAYS) -print -delete
	@echo "Done. Remaining:"
	@ls -1 $(BACKUP_DIR)/aierp_*.dump 2>/dev/null | wc -l

db-shell: ## Open psql shell to dev database
	PGPASSWORD=aierp psql -h localhost -U aierp -d aierp

# ===========================================================================
# Dependency management (Stage 6 Day 4)
# ===========================================================================
deps-update: deps-audit ## Update all dependencies and re-audit
	@echo "=== Updating Python deps ==="
	cd $(BACKEND_DIR) && pip install --upgrade -r requirements.txt
	@echo ""
	@echo "=== Updating Node deps ==="
	cd $(FRONTEND_DIR) && npm update
	@echo ""
	@echo "Re-running security audit..."
	@$(MAKE) deps-audit

deps-audit: ## Audit dependencies for known vulnerabilities
	@echo "=== Backend (pip-audit) ==="
	cd $(BACKEND_DIR) && pip-audit --strict -r requirements.txt || echo "  ⚠️  Vulns found (see docs/DEPENDENCY_AUDIT.md)"
	@echo ""
	@echo "=== Frontend (npm audit) ==="
	cd $(FRONTEND_DIR) && npm audit --audit-level=high

# ===========================================================================
# Operations alerts (Stage 6 Day 2)
# ===========================================================================
ops-alert: ## Run ops health check + Telegram alert
	TELEGRAM_BOT_TOKEN=$${TELEGRAM_BOT_TOKEN:-} ./scripts/ops-alert.sh

ops-alert-cron: ## Show cron line to install ops-alert hourly
	@echo "0 * * * * /home/ttdiy/aierp/scripts/ops-alert.sh >> /home/ttdiy/aierp/logs/ops-alert.log 2>&1"
	@echo ""
	@echo "To install: (crontab -l 2>/dev/null; cat <(echo '0 * * * * /home/ttdiy/aierp/scripts/ops-alert.sh >> /home/ttdiy/aierp/logs/ops-alert.log 2>&1')) | crontab -"

# ===========================================================================
# AlertManager webhook receiver (Stage 10 Day 4)
# ===========================================================================
alert-webhook-start: ## Start AlertManager webhook receiver (port 9099)
	./scripts/alert-webhook.sh start

alert-webhook-stop: ## Stop AlertManager webhook receiver
	./scripts/alert-webhook.sh stop

alert-webhook-status: ## Check webhook receiver status
	./scripts/alert-webhook.sh status

alert-webhook-logs: ## Tail webhook receiver logs (Ctrl+C to exit)
	./scripts/alert-webhook.sh logs

alert-webhook-test: ## Send a test alert to the webhook
	@curl -s -X POST http://localhost:9099/alert \
	  -H 'Content-Type: application/json' \
	  -d '{"version":"4","status":"firing","alerts":[{"status":"firing","labels":{"alertname":"TestAlert","severity":"warning","service":"aierp"},"annotations":{"summary":"Test from Makefile","description":"This is a test alert from make alert-webhook-test"},"startsAt":"2026-06-11T00:00:00Z"}]}'

# ===========================================================================
# Docker (Stage 6 Day 4)
# ===========================================================================
docker-build: ## Build all Docker images (backend + frontend)
	docker compose build

docker-up: ## Start all services via docker compose (detached)
	docker compose up -d
	@echo ""
	@echo "Backend:  http://localhost:8080"
	@echo "Frontend: http://localhost:80"
	@echo "DB:       localhost:5432 (user/pass: aierp/aierp)"

docker-down: ## Stop all services
	docker compose down

docker-logs: ## Tail docker compose logs
	docker compose logs -f --tail=100

docker-ps: ## Show running containers
	docker compose ps

# ---------------------------------------------------------------------------
# Performance baseline (Locust)
# ---------------------------------------------------------------------------
# Usage:
#   make perf-baseline            # interactive web UI on :8089
#   make perf-smoke               # 10 users / 60s
#   make perf-peak                # 25 users / 5min sustained (SLO run)
#   make perf-saturated           # 100 users / 60s (find breaking point)
#
# Requires the venv at /tmp/opencode/locust-venv (or override LOCUST).
# Install with:  python3 -m venv /tmp/opencode/locust-venv && \
#                 /tmp/opencode/locust-venv/bin/pip install locust==2.32.0
LOCUST ?= /tmp/opencode/locust-venv/bin/locust
PERF_DIR := perf
PERF_HOST ?= http://localhost:8080

perf-baseline: ## Locust interactive web UI
	$(LOCUST) -f $(PERF_DIR)/locustfile.py --host $(PERF_HOST)

perf-smoke: ## 10 users / 60s smoke test
	$(LOCUST) -f $(PERF_DIR)/locustfile.py --host $(PERF_HOST) --headless \
		--users 10 --spawn-rate 5 --run-time 60s \
		--csv $(PERF_DIR)/baseline-10u --html $(PERF_DIR)/baseline-10u.html

perf-peak: ## 25 users / 5min sustained (SLO verification)
	$(LOCUST) -f $(PERF_DIR)/locustfile.py --host $(PERF_HOST) --headless \
		--users 25 --spawn-rate 5 --run-time 300s \
		--csv $(PERF_DIR)/baseline-sustained-25u --html $(PERF_DIR)/baseline-sustained-25u.html

perf-saturated: ## 100 users / 60s (find breaking point)
	$(LOCUST) -f $(PERF_DIR)/locustfile.py --host $(PERF_HOST) --headless \
		--users 100 --spawn-rate 10 --run-time 60s \
		--csv $(PERF_DIR)/baseline-100u --html $(PERF_DIR)/baseline-100u.html
