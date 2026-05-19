"""Customer API tests."""
from datetime import datetime, timedelta, timezone

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
        assert resp.json()["data"]["created_at"]

        cid = resp.json()["data"]["id"]
        detail = await async_client.get(f"/api/v1/customers/{cid}", headers=auth_headers)
        assert detail.json()["data"]["created_at"]

        customers = await async_client.get("/api/v1/customers", headers=auth_headers)
        row = next(item for item in customers.json()["data"]["list"] if item["id"] == cid)
        assert row["created_at"]

    async def test_create_customer_auto_generates_short_name(self, async_client: AsyncClient, auth_headers: dict):
        resp = await async_client.post(
            "/api/v1/customers",
            headers=auth_headers,
            json={"name": "深圳市星河电子有限公司", "type": "终端客户"},
        )
        assert resp.status_code == 201
        cid = resp.json()["data"]["id"]

        detail = await async_client.get(f"/api/v1/customers/{cid}", headers=auth_headers)
        assert detail.status_code == 200
        assert detail.json()["data"]["short_name"] == "深圳市星河电子"

    async def test_create_customer_keeps_manual_short_name(self, async_client: AsyncClient, auth_headers: dict):
        resp = await async_client.post(
            "/api/v1/customers",
            headers=auth_headers,
            json={"name": "上海星河电子有限公司", "short_name": "星河", "type": "终端客户"},
        )
        assert resp.status_code == 201
        cid = resp.json()["data"]["id"]

        detail = await async_client.get(f"/api/v1/customers/{cid}", headers=auth_headers)
        assert detail.status_code == 200
        assert detail.json()["data"]["short_name"] == "星河"

    async def test_create_customer_dedupes_auto_short_name_conflicts(self, async_client: AsyncClient, auth_headers: dict):
        first = await async_client.post(
            "/api/v1/customers",
            headers=auth_headers,
            json={"name": "冲突简称电子有限公司", "type": "终端客户"},
        )
        second = await async_client.post(
            "/api/v1/customers",
            headers=auth_headers,
            json={"name": "冲突简称电子有限公司", "type": "终端客户"},
        )
        assert first.status_code == 201
        assert second.status_code == 201

        first_detail = await async_client.get(f"/api/v1/customers/{first.json()['data']['id']}", headers=auth_headers)
        second_detail = await async_client.get(f"/api/v1/customers/{second.json()['data']['id']}", headers=auth_headers)
        first_short_name = first_detail.json()["data"]["short_name"]
        second_short_name = second_detail.json()["data"]["short_name"]

        assert first_short_name == "冲突简称电子"
        assert second_short_name.startswith("冲突简称电子-")
        assert second_short_name != first_short_name

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

    async def test_ai_recognize_customer(self, async_client: AsyncClient, auth_headers: dict, monkeypatch):
        async def fake_recognize_customer(text: str):
            assert "深圳市星河电子有限公司" in text
            return {
                "name": "深圳市星河电子有限公司",
                "short_name": "星河电子",
                "customer_type": "OEM",
                "industry": "汽车电子",
                "level": "A",
                "region": "华南",
                "source": "展会",
                "contact_person": "张工",
                "phone": "13800001111",
                "email": "zhang@example.com",
                "owner": "王明",
                "credit_limit": 200000,
                "credit_level": "A",
                "address": "深圳市南山区",
                "notes": "展会线索",
                "confidence": 0.9,
                "summary": "识别为华南汽车电子OEM客户",
            }

        monkeypatch.setattr(
            "app.api.v1.ai.customer_ai.CustomerAgent.recognize_customer",
            fake_recognize_customer,
        )

        resp = await async_client.post(
            "/api/v1/ai/customer/recognition",
            headers=auth_headers,
            json={"text": "深圳市星河电子有限公司，汽车电子OEM，联系人张工，13800001111，展会线索。"},
        )

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["name"] == "深圳市星河电子有限公司"
        assert data["customer_type"] == "OEM"
        assert data["industry"] == "汽车电子"
        assert data["region"] == "华南"
        assert data["credit_limit"] == 200000
        assert data["confidence"] == 0.9


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

    async def test_ai_recognize_followup(self, async_client: AsyncClient, auth_headers: dict, monkeypatch):
        cust = await async_client.post(
            "/api/v1/customers",
            headers=auth_headers,
            json={"name": "AI识别跟进客户", "type": "终端客户"},
        )
        cid = cust.json()["data"]["id"]

        async def fake_recognize_followup(text: str, customer_data: dict, now_text: str):
            assert "明天下午3点" in text
            assert customer_data["name"] == "AI识别跟进客户"
            assert now_text
            return {
                "method": "phone",
                "status": "planned",
                "priority": "high",
                "content": "客户需要重新评估BOM价格",
                "result": "",
                "planned_at": "2026-05-20 15:00:00",
                "completed_at": "",
                "assigned_to": "王明",
                "confidence": 0.86,
                "summary": "识别为高优先级电话跟进计划",
            }

        monkeypatch.setattr(
            "app.api.v1.ai.customer_ai.CustomerAgent.recognize_followup",
            fake_recognize_followup,
        )

        resp = await async_client.post(
            f"/api/v1/ai/customer/{cid}/followup-recognition",
            headers=auth_headers,
            json={"text": "今天和客户电话沟通，明天下午3点再电话确认BOM价格，优先级高，负责人王明。"},
        )

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["method"] == "phone"
        assert data["status"] == "planned"
        assert data["priority"] == "high"
        assert data["planned_at"] == "2026-05-20 15:00:00"
        assert data["assigned_to"] == "王明"
        assert data["confidence"] == 0.86


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

    async def test_overdue_followups_only_include_scheduled_open_items(self, async_client: AsyncClient, auth_headers: dict):
        cust = await async_client.post(
            "/api/v1/customers",
            headers=auth_headers,
            json={"name": "跟进提醒客户", "type": "终端客户"},
        )
        cid = cust.json()["data"]["id"]

        unscheduled = await async_client.post(
            f"/api/v1/customers/{cid}/follow-ups",
            headers=auth_headers,
            json={"method": "phone", "status": "planned", "content": "无计划时间"},
        )
        assert unscheduled.status_code == 201

        past_time = (datetime.now(timezone.utc) - timedelta(days=3)).isoformat()
        scheduled = await async_client.post(
            f"/api/v1/customers/{cid}/follow-ups",
            headers=auth_headers,
            json={"method": "phone", "status": "planned", "planned_at": past_time},
        )
        scheduled_id = scheduled.json()["data"]["id"]

        overdue = await async_client.get("/api/v1/customers/overdue-followups", headers=auth_headers)
        overdue_ids = {item["id"] for item in overdue.json()["data"]["items"]}
        assert scheduled_id in overdue_ids
        assert unscheduled.json()["data"]["id"] not in overdue_ids

        await async_client.put(
            f"/api/v1/customers/{cid}/follow-ups/{scheduled_id}",
            headers=auth_headers,
            json={"status": "completed"},
        )
        overdue_after_complete = await async_client.get("/api/v1/customers/overdue-followups", headers=auth_headers)
        overdue_ids_after_complete = {item["id"] for item in overdue_after_complete.json()["data"]["items"]}
        assert scheduled_id not in overdue_ids_after_complete

    async def test_follow_up_reminders_group_by_due_bucket(self, async_client: AsyncClient, auth_headers: dict):
        cust = await async_client.post(
            "/api/v1/customers",
            headers=auth_headers,
            json={"name": "提醒分组客户", "type": "终端客户"},
        )
        cid = cust.json()["data"]["id"]
        now = datetime.now(timezone.utc)

        past = await async_client.post(
            f"/api/v1/customers/{cid}/follow-ups",
            headers=auth_headers,
            json={"method": "phone", "status": "planned", "planned_at": (now - timedelta(days=2)).isoformat()},
        )
        today = await async_client.post(
            f"/api/v1/customers/{cid}/follow-ups",
            headers=auth_headers,
            json={"method": "email", "status": "planned", "planned_at": now.isoformat()},
        )
        upcoming = await async_client.post(
            f"/api/v1/customers/{cid}/follow-ups",
            headers=auth_headers,
            json={"method": "visit", "status": "planned", "planned_at": (now + timedelta(days=3)).isoformat()},
        )

        resp = await async_client.get("/api/v1/customers/follow-up-reminders", headers=auth_headers)
        assert resp.status_code == 200
        items_by_id = {item["id"]: item for item in resp.json()["data"]["items"]}
        assert items_by_id[past.json()["data"]["id"]]["due_bucket"] == "overdue"
        assert items_by_id[today.json()["data"]["id"]]["due_bucket"] == "today"
        assert items_by_id[upcoming.json()["data"]["id"]]["due_bucket"] == "upcoming"

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
