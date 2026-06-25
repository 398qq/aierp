"""Tests for Phase 5/6 API modules — approvals, permissions, finance, notifications, procurement, reports, integrations."""

from httpx import AsyncClient


class TestApprovals:
    """Approval rules and requests."""

    async def test_list_rules_empty(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        resp = await async_client.get("/api/v1/approvals/rules", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["code"] == 0

    async def test_create_rule(self, async_client: AsyncClient, admin_headers: dict):
        resp = await async_client.post(
            "/api/v1/approvals/rules",
            headers=admin_headers,
            json={"doc_type": "quotation", "min_amount": 1000, "enabled": True},
        )
        assert resp.status_code == 201
        assert resp.json()["code"] == 0
        assert "id" in resp.json()["data"]

    async def test_create_rule_invalid_doc_type(
        self, async_client: AsyncClient, admin_headers: dict
    ):
        resp = await async_client.post(
            "/api/v1/approvals/rules",
            headers=admin_headers,
            json={"doc_type": "invoice", "min_amount": 0},
        )
        assert resp.json()["code"] != 0

    async def test_update_rule(self, async_client: AsyncClient, admin_headers: dict):
        c = await async_client.post(
            "/api/v1/approvals/rules",
            headers=admin_headers,
            json={"doc_type": "purchase_order", "min_amount": 500},
        )
        rid = c.json()["data"]["id"]
        resp = await async_client.put(
            f"/api/v1/approvals/rules/{rid}",
            headers=admin_headers,
            json={"doc_type": "purchase_order", "min_amount": 2000, "enabled": False},
        )
        assert resp.status_code == 200
        assert resp.json()["code"] == 0

    async def test_delete_rule(self, async_client: AsyncClient, admin_headers: dict):
        c = await async_client.post(
            "/api/v1/approvals/rules",
            headers=admin_headers,
            json={"doc_type": "quotation", "min_amount": 100},
        )
        rid = c.json()["data"]["id"]
        resp = await async_client.delete(
            f"/api/v1/approvals/rules/{rid}", headers=admin_headers
        )
        assert resp.status_code == 200
        assert resp.json()["code"] == 0

    async def test_list_requests_empty(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        resp = await async_client.get(
            "/api/v1/approvals/requests", headers=auth_headers
        )
        assert resp.status_code == 200
        assert resp.json()["code"] == 0

    async def test_list_requests_with_filter(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        resp = await async_client.get(
            "/api/v1/approvals/requests?status=pending&doc_type=quotation",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["code"] == 0

    async def test_rule_requires_permission(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        resp = await async_client.post(
            "/api/v1/approvals/rules",
            headers=auth_headers,
            json={"doc_type": "quotation", "min_amount": 0},
        )
        assert resp.status_code == 403


class TestPermissions:
    """RBAC permissions and roles."""

    async def test_list_permissions(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        resp = await async_client.get("/api/v1/permissions", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["code"] == 0
        data = resp.json()["data"]
        assert "groups" in data
        assert "total" in data

    async def test_list_roles_admin(
        self, async_client: AsyncClient, admin_headers: dict
    ):
        resp = await async_client.get(
            "/api/v1/permissions/roles", headers=admin_headers
        )
        assert resp.status_code == 200
        assert resp.json()["code"] == 0

    async def test_list_roles_requires_permission(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        resp = await async_client.get("/api/v1/permissions/roles", headers=auth_headers)
        assert resp.status_code == 403

    async def test_list_audit_logs(
        self, async_client: AsyncClient, admin_headers: dict
    ):
        resp = await async_client.get(
            "/api/v1/permissions/audit-logs", headers=admin_headers
        )
        assert resp.status_code == 200
        assert resp.json()["code"] == 0


class TestFinanceAccounts:
    """Chart of accounts, journal entries, P&L, bank reconciliation."""

    async def _create_journal_accounts(
        self, async_client: AsyncClient, admin_headers: dict
    ) -> tuple[int, int]:
        debit = await async_client.post(
            "/api/v1/finance/accounts",
            headers=admin_headers,
            json={"code": "6601", "name": "测试费用", "type": "expense"},
        )
        credit = await async_client.post(
            "/api/v1/finance/accounts",
            headers=admin_headers,
            json={"code": "1002", "name": "测试银行", "type": "asset"},
        )
        assert debit.status_code == 201
        assert credit.status_code == 201
        return debit.json()["data"]["id"], credit.json()["data"]["id"]

    async def test_list_accounts(self, async_client: AsyncClient, admin_headers: dict):
        resp = await async_client.get("/api/v1/finance/accounts", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json()["code"] == 0

    async def test_create_account(self, async_client: AsyncClient, admin_headers: dict):
        resp = await async_client.post(
            "/api/v1/finance/accounts",
            headers=admin_headers,
            json={"code": "1002", "name": "银行存款", "type": "asset"},
        )
        assert resp.status_code == 201
        assert resp.json()["code"] == 0
        assert "id" in resp.json()["data"]

    async def test_create_account_invalid_type(
        self, async_client: AsyncClient, admin_headers: dict
    ):
        resp = await async_client.post(
            "/api/v1/finance/accounts",
            headers=admin_headers,
            json={"code": "9999", "name": "Invalid", "type": "invalid"},
        )
        assert resp.json()["code"] != 0

    async def test_account_requires_permission(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        resp = await async_client.get("/api/v1/finance/accounts", headers=auth_headers)
        assert resp.status_code == 403

    async def test_create_journal_entry_balanced(
        self, async_client: AsyncClient, admin_headers: dict
    ):
        debit_account_id, credit_account_id = await self._create_journal_accounts(
            async_client, admin_headers
        )
        resp = await async_client.post(
            "/api/v1/finance/journal-entries",
            headers=admin_headers,
            json={
                "entry_date": "2025-01-15",
                "description": "采购原料",
                "lines": [
                    {"account_id": debit_account_id, "debit": 1000, "credit": 0},
                    {"account_id": credit_account_id, "debit": 0, "credit": 1000},
                ],
            },
        )
        assert resp.status_code == 201
        assert resp.json()["code"] == 0
        assert "entry_no" in resp.json()["data"]

    async def test_create_journal_entry_unbalanced(
        self, async_client: AsyncClient, admin_headers: dict
    ):
        resp = await async_client.post(
            "/api/v1/finance/journal-entries",
            headers=admin_headers,
            json={
                "entry_date": "2025-01-15",
                "description": "Unbalanced entry",
                "lines": [
                    {"account_id": 1, "debit": 1000, "credit": 0},
                    {"account_id": 2, "debit": 0, "credit": 500},
                ],
            },
        )
        assert resp.json()["code"] != 0

    async def test_list_journal_entries(
        self, async_client: AsyncClient, admin_headers: dict
    ):
        debit_account_id, credit_account_id = await self._create_journal_accounts(
            async_client, admin_headers
        )
        # Create an entry first
        await async_client.post(
            "/api/v1/finance/journal-entries",
            headers=admin_headers,
            json={
                "entry_date": "2025-01-10",
                "description": "Test entry",
                "lines": [
                    {"account_id": debit_account_id, "debit": 500, "credit": 0},
                    {"account_id": credit_account_id, "debit": 0, "credit": 500},
                ],
            },
        )
        resp = await async_client.get(
            "/api/v1/finance/journal-entries", headers=admin_headers
        )
        assert resp.status_code == 200
        assert resp.json()["code"] == 0

    async def test_pnl_report(self, async_client: AsyncClient, admin_headers: dict):
        resp = await async_client.get(
            "/api/v1/finance/reports/pnl?month=2025-01", headers=admin_headers
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "revenue" in data
        assert "net_profit" in data

    async def test_ap_report(self, async_client: AsyncClient, admin_headers: dict):
        resp = await async_client.get(
            "/api/v1/finance/reports/ap", headers=admin_headers
        )
        assert resp.status_code == 200
        assert resp.json()["code"] == 0

    async def test_account_crud_lifecycle(
        self, async_client: AsyncClient, admin_headers: dict
    ):
        # Create
        c = await async_client.post(
            "/api/v1/finance/accounts",
            headers=admin_headers,
            json={"code": "5001", "name": "TestAccount", "type": "income"},
        )
        assert c.status_code == 201
        aid = c.json()["data"]["id"]
        # Update
        u = await async_client.put(
            f"/api/v1/finance/accounts/{aid}",
            headers=admin_headers,
            json={"code": "5001", "name": "UpdatedAccount", "type": "income"},
        )
        assert u.json()["code"] == 0
        # Delete
        d = await async_client.delete(
            f"/api/v1/finance/accounts/{aid}", headers=admin_headers
        )
        assert d.json()["code"] == 0


class TestNotifications:
    """Notification listing, templates, preferences."""

    async def test_list_notifications(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        resp = await async_client.get("/api/v1/notifications", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["code"] == 0

    async def test_unread_count(self, async_client: AsyncClient, auth_headers: dict):
        resp = await async_client.get(
            "/api/v1/notifications/unread-count", headers=auth_headers
        )
        assert resp.status_code == 200
        assert resp.json()["code"] == 0

    async def test_list_templates_admin(
        self, async_client: AsyncClient, admin_headers: dict
    ):
        resp = await async_client.get(
            "/api/v1/notifications/templates", headers=admin_headers
        )
        assert resp.status_code == 200
        assert resp.json()["code"] == 0

    async def test_templates_require_permission(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        resp = await async_client.get(
            "/api/v1/notifications/templates", headers=auth_headers
        )
        assert resp.status_code == 403

    async def test_preferences_crud(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        # Get empty
        resp = await async_client.get(
            "/api/v1/notifications/preferences", headers=auth_headers
        )
        assert resp.status_code == 200
        # Save
        resp = await async_client.put(
            "/api/v1/notifications/preferences",
            headers=auth_headers,
            json={
                "preferences": [
                    {
                        "event_type": "order_created",
                        "channel": "in_app",
                        "enabled": True,
                    },
                ]
            },
        )
        assert resp.status_code == 200
        assert resp.json()["code"] == 0
        # Verify saved
        resp = await async_client.get(
            "/api/v1/notifications/preferences", headers=auth_headers
        )
        assert len(resp.json()["data"]) > 0


class TestProcurement:
    """AI procurement intelligence."""

    async def test_restock_suggest(
        self, async_client: AsyncClient, admin_headers: dict
    ):
        resp = await async_client.get(
            "/api/v1/ai/procurement/restock-suggest", headers=admin_headers
        )
        assert resp.status_code == 200
        assert resp.json()["code"] == 0

    async def test_restock_requires_permission(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        resp = await async_client.get(
            "/api/v1/ai/procurement/restock-suggest", headers=auth_headers
        )
        assert resp.status_code == 403


class TestReports:
    """Reports module — sales, inventory, procurement, AR."""

    async def test_report_sales(self, async_client: AsyncClient, admin_headers: dict):
        resp = await async_client.get(
            "/api/v1/reports/predefined/sales?year=2025&month=1", headers=admin_headers
        )
        assert resp.status_code == 200
        assert resp.json()["code"] == 0

    async def test_report_inventory(
        self, async_client: AsyncClient, admin_headers: dict
    ):
        resp = await async_client.get(
            "/api/v1/reports/predefined/inventory", headers=admin_headers
        )
        assert resp.status_code == 200
        assert resp.json()["code"] == 0

    async def test_report_procurement(
        self, async_client: AsyncClient, admin_headers: dict
    ):
        resp = await async_client.get(
            "/api/v1/reports/predefined/procurement?year=2025&month=1",
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["code"] == 0

    async def test_report_ar(self, async_client: AsyncClient, admin_headers: dict):
        resp = await async_client.get(
            "/api/v1/reports/predefined/ar", headers=admin_headers
        )
        assert resp.status_code == 200
        assert resp.json()["code"] == 0

    async def test_reports_require_permission(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        resp = await async_client.get(
            "/api/v1/reports/predefined/sales?year=2025&month=1", headers=auth_headers
        )
        assert resp.status_code == 403

    async def test_list_templates(self, async_client: AsyncClient, admin_headers: dict):
        resp = await async_client.get(
            "/api/v1/reports/templates", headers=admin_headers
        )
        assert resp.status_code == 200
        assert resp.json()["code"] == 0


class TestIntegrations:
    """Integration configs and data import."""

    async def test_list_configs_empty(
        self, async_client: AsyncClient, admin_headers: dict
    ):
        resp = await async_client.get(
            "/api/v1/integrations/configs", headers=admin_headers
        )
        assert resp.status_code == 200
        assert resp.json()["code"] == 0

    async def test_create_config(self, async_client: AsyncClient, admin_headers: dict):
        resp = await async_client.post(
            "/api/v1/integrations/configs",
            headers=admin_headers,
            json={
                "type": "ecommerce",
                "name": "Taobao Store",
                "api_key": "key123",
                "api_secret": "secret456",
                "endpoint": "https://api.taobao.com",
                "enabled": False,
            },
        )
        assert resp.status_code == 201
        assert resp.json()["code"] == 0

    async def test_update_config(self, async_client: AsyncClient, admin_headers: dict):
        c = await async_client.post(
            "/api/v1/integrations/configs",
            headers=admin_headers,
            json={"type": "logistics", "name": "Cainiao"},
        )
        cid = c.json()["data"]["id"]
        resp = await async_client.put(
            f"/api/v1/integrations/configs/{cid}",
            headers=admin_headers,
            json={"type": "logistics", "name": "Cainiao Updated", "enabled": True},
        )
        assert resp.status_code == 200
        assert resp.json()["code"] == 0

    async def test_delete_config(self, async_client: AsyncClient, admin_headers: dict):
        c = await async_client.post(
            "/api/v1/integrations/configs",
            headers=admin_headers,
            json={"type": "webhook", "name": "Test Webhook"},
        )
        cid = c.json()["data"]["id"]
        resp = await async_client.delete(
            f"/api/v1/integrations/configs/{cid}", headers=admin_headers
        )
        assert resp.status_code == 200
        assert resp.json()["code"] == 0

    async def test_configs_require_permission(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        resp = await async_client.post(
            "/api/v1/integrations/configs",
            headers=auth_headers,
            json={"type": "ecommerce", "name": "Test"},
        )
        assert resp.status_code == 403

    async def test_order_import_reuses_normalized_existing_customer(
        self, async_client: AsyncClient, admin_headers: dict
    ):
        await async_client.post(
            "/api/v1/customers",
            headers=admin_headers,
            json={"name": "深圳市华芯科技有限公司", "phone": "13800001111"},
        )
        csv_data = (
            "buyer_name,buyer_phone,quantity,price\n深圳华芯科技,13900002222,1,10"
        )

        resp = await async_client.post(
            "/api/v1/integrations/orders/import",
            headers=admin_headers,
            files={"file": ("orders.csv", csv_data.encode("utf-8-sig"), "text/csv")},
        )

        assert resp.status_code == 200
        assert resp.json()["data"]["created_orders"] == 1
        assert resp.json()["data"]["created_customers"] == 0

        listed = await async_client.get(
            "/api/v1/customers?q=华芯科技", headers=admin_headers
        )
        assert listed.json()["data"]["total"] == 1

    async def test_logistics_tracking(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        resp = await async_client.get(
            "/api/v1/integrations/logistics/TRACK123", headers=auth_headers
        )
        assert resp.status_code == 200
        assert resp.json()["code"] == 0
