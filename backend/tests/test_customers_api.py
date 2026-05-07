"""Customer API tests."""
import pytest
from httpx import AsyncClient


class TestCustomers:
    """Customer CRUD + batch operations."""

    async def test_list_empty(self, async_client: AsyncClient, auth_headers: dict):
        resp = await async_client.get("/api/v1/customers", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["code"] == 0

    async def test_create_customer(self, async_client: AsyncClient, auth_headers: dict):
        resp = await async_client.post(
            "/api/v1/customers",
            headers=auth_headers,
            json={"name": "测试客户", "type": "终端客户", "industry": "工业"},
        )
        assert resp.status_code == 201
        assert resp.json()["code"] == 0
        assert "id" in resp.json()["data"]

    async def test_get_customer(self, async_client: AsyncClient, auth_headers: dict):
        c = await async_client.post(
            "/api/v1/customers",
            headers=auth_headers,
            json={"name": "单个客户", "type": "终端客户"},
        )
        cid = c.json()["data"]["id"]
        resp = await async_client.get(f"/api/v1/customers/{cid}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["data"]["name"] == "单个客户"

    async def test_update_customer(self, async_client: AsyncClient, auth_headers: dict):
        c = await async_client.post(
            "/api/v1/customers",
            headers=auth_headers,
            json={"name": "原始", "type": "终端客户"},
        )
        cid = c.json()["data"]["id"]
        resp = await async_client.put(
            f"/api/v1/customers/{cid}",
            headers=auth_headers,
            json={"name": "已更新"},
        )
        assert resp.status_code == 200
        assert resp.json()["code"] == 0

    async def test_delete_customer(self, async_client: AsyncClient, auth_headers: dict):
        c = await async_client.post(
            "/api/v1/customers",
            headers=auth_headers,
            json={"name": "待删除", "type": "终端客户"},
        )
        cid = c.json()["data"]["id"]
        resp = await async_client.delete(f"/api/v1/customers/{cid}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["code"] == 0

    async def test_batch_delete(self, async_client: AsyncClient, auth_headers: dict):
        c1 = await async_client.post(
            "/api/v1/customers", headers=auth_headers,
            json={"name": "批量删1", "type": "终端客户"},
        )
        c2 = await async_client.post(
            "/api/v1/customers", headers=auth_headers,
            json={"name": "批量删2", "type": "终端客户"},
        )
        ids = [c1.json()["data"]["id"], c2.json()["data"]["id"]]
        resp = await async_client.post(
            "/api/v1/customers/batch-delete",
            headers=auth_headers,
            json={"ids": ids},
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["deleted"] == 2

    async def test_unauthorized(self, async_client: AsyncClient):
        resp = await async_client.get("/api/v1/customers")
        assert resp.status_code == 401


class TestCustomerContacts:
    """Contact management."""

    async def test_add_contact(self, async_client: AsyncClient, auth_headers: dict):
        cust = await async_client.post(
            "/api/v1/customers",
            headers=auth_headers,
            json={"name": "联系人测试客户", "type": "终端客户"},
        )
        cid = cust.json()["data"]["id"]
        resp = await async_client.post(
            f"/api/v1/customers/{cid}/contacts",
            headers=auth_headers,
            json={"name": "张三", "phone": "13800001111"},
        )
        assert resp.status_code == 201
        assert resp.json()["code"] == 0

    async def test_list_contacts(self, async_client: AsyncClient, auth_headers: dict):
        cust = await async_client.post(
            "/api/v1/customers",
            headers=auth_headers,
            json={"name": "列表联系人", "type": "终端客户"},
        )
        cid = cust.json()["data"]["id"]
        resp = await async_client.get(f"/api/v1/customers/{cid}/contacts", headers=auth_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json()["data"], list)

    async def test_delete_contact(self, async_client: AsyncClient, auth_headers: dict):
        cust = await async_client.post(
            "/api/v1/customers",
            headers=auth_headers,
            json={"name": "删除联系人", "type": "终端客户"},
        )
        cid = cust.json()["data"]["id"]
        contact = await async_client.post(
            f"/api/v1/customers/{cid}/contacts",
            headers=auth_headers,
            json={"name": "李四", "phone": "13800001112"},
        )
        contact_id = contact.json()["data"]["id"]
        resp = await async_client.delete(
            f"/api/v1/customers/{cid}/contacts/{contact_id}",
            headers=auth_headers,
        )
        assert resp.status_code == 200


class TestCustomerFollowups:
    """Follow-up records."""

    async def test_add_followup(self, async_client: AsyncClient, auth_headers: dict):
        cust = await async_client.post(
            "/api/v1/customers",
            headers=auth_headers,
            json={"name": "跟进测试", "type": "终端客户"},
        )
        cid = cust.json()["data"]["id"]
        resp = await async_client.post(
            f"/api/v1/customers/{cid}/follow-ups",
            headers=auth_headers,
            json={"content": "初次拜访", "type": "拜访"},
        )
        assert resp.status_code == 201
        assert resp.json()["code"] == 0

    async def test_list_followups(self, async_client: AsyncClient, auth_headers: dict):
        cust = await async_client.post(
            "/api/v1/customers",
            headers=auth_headers,
            json={"name": "列表跟进", "type": "终端客户"},
        )
        cid = cust.json()["data"]["id"]
        resp = await async_client.get(f"/api/v1/customers/{cid}/follow-ups", headers=auth_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json()["data"], list)

    async def test_update_followup(self, async_client: AsyncClient, auth_headers: dict):
        cust = await async_client.post(
            "/api/v1/customers",
            headers=auth_headers,
            json={"name": "更新跟进", "type": "终端客户"},
        )
        cid = cust.json()["data"]["id"]
        fup = await async_client.post(
            f"/api/v1/customers/{cid}/follow-ups",
            headers=auth_headers,
            json={"content": "原始内容", "type": "拜访"},
        )
        fup_id = fup.json()["data"]["id"]
        resp = await async_client.put(
            f"/api/v1/customers/{cid}/follow-ups/{fup_id}",
            headers=auth_headers,
            json={"content": "已更新内容"},
        )
        assert resp.status_code == 200


class TestCustomerStats:
    """Customer analytics endpoints."""

    async def test_customer_stats(self, async_client: AsyncClient, auth_headers: dict):
        cust = await async_client.post(
            "/api/v1/customers",
            headers=auth_headers,
            json={"name": "统计客户", "type": "终端客户"},
        )
        cid = cust.json()["data"]["id"]
        resp = await async_client.get(f"/api/v1/customers/{cid}/stats", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["code"] == 0

    async def test_customer_timeline(self, async_client: AsyncClient, auth_headers: dict):
        cust = await async_client.post(
            "/api/v1/customers",
            headers=auth_headers,
            json={"name": "时间线客户", "type": "终端客户"},
        )
        cid = cust.json()["data"]["id"]
        resp = await async_client.get(f"/api/v1/customers/{cid}/timeline", headers=auth_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json()["data"], list)

    async def test_overdue_followups(self, async_client: AsyncClient, auth_headers: dict):
        resp = await async_client.get("/api/v1/customers/overdue-followups", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["code"] == 0

    async def test_customer_alerts(self, async_client: AsyncClient, auth_headers: dict):
        resp = await async_client.get("/api/v1/customers/alerts", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["code"] == 0

    async def test_alert_rules_crud(self, async_client: AsyncClient, auth_headers: dict):
        # create
        create = await async_client.post(
            "/api/v1/customers/alerts/rules",
            headers=auth_headers,
            json={"name": "逾期规则", "rule_type": "ar_overdue", "threshold_days": 30},
        )
        assert create.status_code == 201
        rule_id = create.json()["data"]["id"]
        # update
        upd = await async_client.put(
            f"/api/v1/customers/alerts/rules/{rule_id}",
            headers=auth_headers,
            json={"threshold_days": 15},
        )
        assert upd.status_code == 200
        # delete
        del_ = await async_client.delete(
            f"/api/v1/customers/alerts/rules/{rule_id}",
            headers=auth_headers,
        )
        assert del_.status_code == 200


class TestCustomerLevelRules:
    """Customer level (A/B/C) management."""

    async def test_level_rules_crud(self, async_client: AsyncClient, auth_headers: dict):
        # create rule
        create = await async_client.post(
            "/api/v1/customers/level-rules",
            headers=auth_headers,
            json={
                "name": "A类客户规则", "target_level": "A",
                "condition_type": "revenue", "operator": ">=",
                "threshold_value": 100000, "period_days": 365,
            },
        )
        assert create.status_code == 201
        rule_id = create.json()["data"]["id"]
        # update
        upd = await async_client.put(
            f"/api/v1/customers/level-rules/{rule_id}",
            headers=auth_headers,
            json={"threshold_value": 50000},
        )
        assert upd.status_code == 200
        # delete
        del_ = await async_client.delete(
            f"/api/v1/customers/level-rules/{rule_id}",
            headers=auth_headers,
        )
        assert del_.status_code == 200

    async def test_list_level_rules(self, async_client: AsyncClient, auth_headers: dict):
        resp = await async_client.get("/api/v1/customers/level-rules", headers=auth_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json()["data"], list)
