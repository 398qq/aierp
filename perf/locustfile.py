"""
AIERP performance baseline load test.

Simulates realistic ERP user behavior across four roles with weighted traffic.
Records p50/p95/p99 latencies and throughput for the SLO guardrails report.

Run with:
  locust -f perf/locustfile.py --host http://localhost:8080 --headless \
         --users 50 --spawn-rate 10 --run-time 60s --html perf/baseline.html
  locust -f perf/locustfile.py --host http://localhost:8080  # interactive web UI
"""
from __future__ import annotations

import random
import time
from typing import Any

from locust import HttpUser, between, events, task
from locust.exception import RescheduleTask


BASE_PATH = "/api/v1"
ADMIN_USER = "admin"
ADMIN_PASSWORD = "admin123"


class _BaseERPUser(HttpUser):
    """Shared login + token lifecycle for every role."""

    abstract = True
    wait_time = between(0.5, 2.0)
    token: str = ""
    token_acquired_at: float = 0.0
    token_ttl_seconds: int = 8 * 3600  # backend default

    def on_start(self) -> None:
        self._login()

    def _login(self) -> None:
        with self.client.post(
            f"{BASE_PATH}/auth/login",
            json={"username": ADMIN_USER, "password": ADMIN_PASSWORD},
            name="POST /auth/login",
            catch_response=True,
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"login failed: {resp.status_code} {resp.text[:120]}")
                raise RescheduleTask()
            payload = resp.json()
            data = payload.get("data") or {}
            self.token = data.get("token") or data.get("access_token") or ""
            if not self.token:
                resp.failure("no token in response")
                raise RescheduleTask()
            self.token_acquired_at = time.time()
            self._headers = {"Authorization": f"Bearer {self.token}"}

    def _ensure_token(self) -> None:
        # Re-login if token is close to expiry.
        if time.time() - self.token_acquired_at > self.token_ttl_seconds - 60:
            self._login()

    def _get(self, path: str, name: str) -> Any:
        self._ensure_token()
        with self.client.get(
            f"{BASE_PATH}{path}",
            headers=self._headers,
            name=name,
            catch_response=True,
        ) as resp:
            if resp.status_code == 401:
                self._login()
                return self._get(path, name)
            if resp.status_code >= 400:
                resp.failure(f"{name} -> {resp.status_code}")
                return None
            try:
                return resp.json()
            except ValueError:
                return None


class SalesClerkUser(_BaseERPUser):
    """Sales clerk: browses customers + products + creates orders. Weight: 50%."""

    weight = 5

    @task(5)
    def list_customers(self) -> None:
        self._get("/customers?page=1&page_size=20", "GET /customers")

    @task(4)
    def list_products(self) -> None:
        self._get("/products?page=1&page_size=20", "GET /products")

    @task(3)
    def list_sales_orders(self) -> None:
        self._get("/sales-orders?page=1&page_size=20", "GET /sales-orders")

    @task(2)
    def list_opportunities(self) -> None:
        self._get("/opportunities?page=1&page_size=20", "GET /opportunities")

    @task(2)
    def list_quotations(self) -> None:
        self._get("/quotations?page=1&page_size=20", "GET /quotations")

    @task(2)
    def quotation_stats(self) -> None:
        self._get("/quotations/stats", "GET /quotations/stats")

    @task(2)
    def dashboard_overview(self) -> None:
        self._get("/sales/dashboard/overview", "GET /sales/dashboard/overview")

    @task(1)
    def dashboard_trends(self) -> None:
        self._get("/sales/dashboard/trends?months=12", "GET /sales/dashboard/trends")

    @task(1)
    def dashboard_alerts(self) -> None:
        self._get("/sales/dashboard/alerts?limit=10", "GET /sales/dashboard/alerts")

    @task(1)
    def dashboard_kpi(self) -> None:
        self._get("/dashboard/kpi", "GET /dashboard/kpi")

    @task(1)
    def get_customer_detail(self) -> None:
        # Pick a random page to discover a customer id.
        body = self._get("/customers?page=1&page_size=20", "GET /customers (find id)")
        if not body:
            return
        items = (body.get("data") or {}).get("list") or []
        if not items:
            return
        cust_id = random.choice(items).get("id")
        if cust_id is not None:
            self._get(f"/customers/{cust_id}", "GET /customers/{id}")


class OperationsUser(_BaseERPUser):
    """Operations: inventory + procurement browsing. Weight: 25%."""

    weight = 3

    @task(5)
    def list_products(self) -> None:
        self._get("/products?page=1&page_size=20", "GET /products")

    @task(4)
    def list_inventory(self) -> None:
        self._get("/inventory?page=1&page_size=20", "GET /inventory")

    @task(2)
    def list_sales_orders(self) -> None:
        self._get("/sales-orders?page=1&page_size=20", "GET /sales-orders")

    @task(1)
    def health_probe(self) -> None:
        # Public health endpoint: validates no-auth path.
        with self.client.get("/health", name="GET /health", catch_response=True) as resp:
            if resp.status_code != 200:
                resp.failure(f"/health -> {resp.status_code}")


class FinanceUser(_BaseERPUser):
    """Finance: sales orders + customer ledger + finance/reports dashboards. Weight: 15%."""

    weight = 2

    @task(4)
    def list_sales_orders(self) -> None:
        self._get("/sales-orders?page=1&page_size=20", "GET /sales-orders")

    @task(3)
    def list_customers(self) -> None:
        self._get("/customers?page=1&page_size=20", "GET /customers")

    @task(2)
    def get_customer_detail(self) -> None:
        body = self._get("/customers?page=1&page_size=20", "GET /customers (find id)")
        if not body:
            return
        items = (body.get("data") or {}).get("list") or []
        if not items:
            return
        cust_id = random.choice(items).get("id")
        if cust_id is not None:
            self._get(f"/customers/{cust_id}", "GET /customers/{id}")

    @task(1)
    def list_products(self) -> None:
        self._get("/products?page=1&page_size=20", "GET /products")

    # ----- v5: finance & reports cache traffic -----
    @task(3)
    def payment_stats(self) -> None:
        self._get("/payments/stats", "GET /payments/stats")

    @task(2)
    def target_stats(self) -> None:
        self._get("/targets/stats", "GET /targets/stats")

    @task(2)
    def list_invoices(self) -> None:
        self._get("/invoices?page=1&page_size=20", "GET /invoices")

    @task(2)
    def list_payments(self) -> None:
        self._get("/payments?page=1&page_size=20", "GET /payments")

    @task(2)
    def list_contracts(self) -> None:
        self._get("/contracts?page=1&page_size=20", "GET /contracts")

    @task(2)
    def pnl_report(self) -> None:
        self._get("/finance/reports/pnl?month=2026-05", "GET /finance/reports/pnl")

    @task(2)
    def ap_report(self) -> None:
        self._get("/finance/reports/ap", "GET /finance/reports/ap")

    @task(2)
    def sales_report(self) -> None:
        self._get("/reports/predefined/sales?months=12", "GET /reports/predefined/sales")

    @task(1)
    def ar_report(self) -> None:
        self._get("/reports/predefined/ar", "GET /reports/predefined/ar")

    @task(1)
    def inventory_report(self) -> None:
        self._get("/reports/predefined/inventory", "GET /reports/predefined/inventory")

    @task(1)
    def procurement_report(self) -> None:
        self._get("/reports/predefined/procurement?months=12", "GET /reports/predefined/procurement")


class AdminUser(_BaseERPUser):
    """Admin: users management + mixed browsing. Weight: 10%."""

    weight = 1

    @task(3)
    def list_users(self) -> None:
        self._get("/users?page=1&page_size=20", "GET /users")

    @task(2)
    def list_customers(self) -> None:
        self._get("/customers?page=1&page_size=20", "GET /customers")

    @task(2)
    def list_products(self) -> None:
        self._get("/products?page=1&page_size=20", "GET /products")

    @task(1)
    def list_sales_orders(self) -> None:
        self._get("/sales-orders?page=1&page_size=20", "GET /sales-orders")


@events.test_start.add_listener
def _on_test_start(environment, **_kwargs: Any) -> None:
    print("\n=== AIERP baseline test starting ===")
    print(f"Target host: {environment.host}")
    print("Roles: SalesClerk 50% / Operations 25% / Finance 15% / Admin 10%\n")


@events.test_stop.add_listener
def _on_test_stop(environment, **_kwargs: Any) -> None:
    stats = environment.stats.total
    print("\n=== AIERP baseline test done ===")
    print(f"Requests: {stats.num_requests}  Failures: {stats.num_failures}  "
          f"Failure rate: {stats.fail_ratio * 100:.2f}%")
    print(f"RPS: {stats.total_rps:.2f}  Median: {stats.median_response_time}ms  "
          f"p95: {stats.get_response_time_percentile(0.95):.0f}ms  "
          f"p99: {stats.get_response_time_percentile(0.99):.0f}ms  "
          f"Max: {stats.max_response_time}ms")
