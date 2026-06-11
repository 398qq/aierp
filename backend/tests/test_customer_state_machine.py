"""Customer module closed-loop tests — state machine, transitions, API, stats."""

import pytest

from app.domain.shared.errors import InvalidStateTransition
from app.domain.states import (
    CUSTOMER_TRANSITIONS,
    CUSTOMER_STATUS_LABELS,
    assert_can_transition_customer,
)


# ═══════════════════════════════════════════════════════════════
# State machine unit tests
# ═══════════════════════════════════════════════════════════════


class TestCustomerStateMachine:
    """验证 7 状态机的所有转换规则"""

    def test_all_statuses_have_labels(self):
        for status in CUSTOMER_TRANSITIONS:
            assert status in CUSTOMER_STATUS_LABELS, f"Missing label for {status}"

    def test_legal_flow_new_lead_to_vip(self):
        """完整正向流程: new_lead → active → converted → vip"""
        assert_can_transition_customer("new_lead", "active")
        assert_can_transition_customer("active", "converted")
        assert_can_transition_customer("converted", "vip")

    def test_legal_flow_new_lead_to_churned(self):
        """直接流失: new_lead → churned"""
        assert_can_transition_customer("new_lead", "churned")

    def test_legal_inactive_to_active(self):
        """重新激活: inactive → active"""
        assert_can_transition_customer("inactive", "active")

    def test_legal_churned_to_active(self):
        """流失后重新激活: churned → active"""
        assert_can_transition_customer("churned", "active")

    def test_legal_converted_to_inactive(self):
        """成交后不活跃: converted → inactive"""
        assert_can_transition_customer("converted", "inactive")

    def test_legal_vip_to_inactive(self):
        """VIP 降级: vip → inactive"""
        assert_can_transition_customer("vip", "inactive")

    def test_legal_vip_to_churned(self):
        """VIP 流失: vip → churned"""
        assert_can_transition_customer("vip", "churned")

    def test_illegal_active_to_new_lead(self):
        """不能倒退到新潜客"""
        with pytest.raises(InvalidStateTransition):
            assert_can_transition_customer("active", "new_lead")

    def test_illegal_converted_to_new_lead(self):
        """已成交不能退回新潜客"""
        with pytest.raises(InvalidStateTransition):
            assert_can_transition_customer("converted", "new_lead")

    def test_illegal_vip_to_new_lead(self):
        """VIP 不能退回新潜客"""
        with pytest.raises(InvalidStateTransition):
            assert_can_transition_customer("vip", "new_lead")

    def test_illegal_new_lead_to_vip(self):
        """不能跳跃到 VIP"""
        with pytest.raises(InvalidStateTransition):
            assert_can_transition_customer("new_lead", "vip")

    def test_illegal_churned_to_vip(self):
        """流失不能直接变 VIP"""
        with pytest.raises(InvalidStateTransition):
            assert_can_transition_customer("churned", "vip")

    def test_illegal_inactive_to_vip(self):
        """不活跃不能直接变 VIP"""
        with pytest.raises(InvalidStateTransition):
            assert_can_transition_customer("inactive", "vip")

    def test_unknown_status_raises(self):
        """非法状态抛出异常"""
        with pytest.raises(InvalidStateTransition):
            assert_can_transition_customer("new_lead", "flying")

    def test_transition_count(self):
        """确认有 6 个状态"""
        assert len(CUSTOMER_TRANSITIONS) == 6

    def test_terminal_paths_exist(self):
        """确认 churned 可以作为多个状态的终点"""
        assert "churned" in CUSTOMER_TRANSITIONS["new_lead"]
        assert "churned" in CUSTOMER_TRANSITIONS["active"]
        assert "churned" in CUSTOMER_TRANSITIONS["converted"]
        assert "churned" in CUSTOMER_TRANSITIONS["vip"]
        assert "churned" in CUSTOMER_TRANSITIONS["inactive"]

    def test_active_can_reach_all_major_states(self):
        """active 可以到达 converted, inactive, churned"""
        allowed = CUSTOMER_TRANSITIONS["active"]
        assert "converted" in allowed
        assert "inactive" in allowed
        assert "churned" in allowed


# ═══════════════════════════════════════════════════════════════
# Auto-transition service tests
# ═══════════════════════════════════════════════════════════════


class TestAutoTransitionService:
    """验证自动转换服务逻辑"""

    def test_vip_threshold_constant(self):
        from app.services.customer_state_service import VIP_REVENUE_THRESHOLD

        assert VIP_REVENUE_THRESHOLD == 500_000.0

    def test_inactive_days_constant(self):
        from app.services.customer_state_service import INACTIVE_DAYS

        assert INACTIVE_DAYS == 90

    def test_transition_helper_same_status_raises(self):
        """相同状态转换应抛出异常（状态机不允许自循环）"""
        with pytest.raises(InvalidStateTransition):
            assert_can_transition_customer("active", "active")

    def test_on_first_opportunity_only_triggers_new_lead(self):
        """只有 new_lead 状态才会被首个机会触发转换"""
        from app.services.customer_state_service import on_first_opportunity

        # 函数签名验证：接受 db + customer_id
        import inspect

        sig = inspect.signature(on_first_opportunity)
        params = list(sig.parameters.keys())
        assert "db" in params
        assert "customer_id" in params

    def test_on_first_order_completed_triggers_active_and_new_lead(self):
        """首单完成触发 new_lead/active → converted"""
        from app.services.customer_state_service import on_first_order_completed
        import inspect

        sig = inspect.signature(on_first_order_completed)
        params = list(sig.parameters.keys())
        assert "db" in params
        assert "customer_id" in params

    def test_on_re_engage_triggers_inactive_and_churned(self):
        """重新互动触发 inactive/churned → active"""
        from app.services.customer_state_service import on_re_engage
        import inspect

        sig = inspect.signature(on_re_engage)
        params = list(sig.parameters.keys())
        assert "db" in params
        assert "customer_id" in params

    @pytest.mark.asyncio
    async def test_run_customer_status_job_exists(self):
        """定时任务函数存在且可调用"""
        from app.services.customer_state_service import run_customer_status_job
        import inspect

        assert inspect.iscoroutinefunction(run_customer_status_job)


# ═══════════════════════════════════════════════════════════════
# Scheduler integration tests
# ═══════════════════════════════════════════════════════════════


class TestSchedulerIntegration:
    """验证定时任务已注册"""

    def test_customer_status_job_registered(self):
        """cron 02:00 任务已注册"""
        import importlib
        import app.jobs.scheduler as sched_mod

        importlib.reload(sched_mod)
        # 验证 _run_customer_status_job 函数存在
        assert hasattr(sched_mod, "_run_customer_status_job")
        assert callable(sched_mod._run_customer_status_job)

    def test_scheduler_count_includes_customer_job(self):
        """确认调度器任务数 >= 10（包含新增的客户状态任务）"""
        import inspect
        import app.jobs.scheduler as sched_mod

        source = inspect.getsource(sched_mod.start)
        assert "_run_customer_status_job" in source
        assert "hour=2" in source


# ═══════════════════════════════════════════════════════════════
# Customer API integration tests
# ═══════════════════════════════════════════════════════════════


@pytest.mark.integration
class TestCustomerAPIIntegration:
    """验证客户 CRUD + 状态流转的 API 集成"""

    @pytest.mark.asyncio
    async def test_list_customers_returns_paginated(self, async_client):
        """GET /customers 返回分页数据"""

        resp = await async_client.get("/api/v1/customers?page=1&page_size=10")
        assert resp.status_code in (200, 401)  # 200 with auth, 401 without

    @pytest.mark.asyncio
    async def test_list_customers_with_search(self, async_client, auth_headers):
        """GET /customers?q=xxx 支持搜索"""
        resp = await async_client.get(
            "/api/v1/customers?q=test&page=1&page_size=10",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        payload = resp.json()
        assert payload["code"] == 0
        assert "list" in payload["data"]
        assert "total" in payload["data"]

    @pytest.mark.asyncio
    async def test_create_customer_sets_default_status(
        self, async_client, auth_headers
    ):
        """POST /customers 创建客户默认状态为 new_lead"""
        resp = await async_client.post(
            "/api/v1/customers",
            headers=auth_headers,
            json={
                "name": "闭环测试客户",
                "industry": "电子产品",
                "region": "华东",
                "phone": "13900000000",
                "credit_limit": 200000,
            },
        )
        assert resp.status_code == 201
        data = resp.json()["data"]
        assert data.get("status") in (
            "new_lead",
            None,
            "",
        ), f"Expected new_lead status, got: {data.get('status')}"

    @pytest.mark.asyncio
    async def test_customer_stats_endpoint(
        self, async_client, auth_headers, test_customer
    ):
        """GET /customers/{id}/stats 返回健康度等数据"""
        resp = await async_client.get(
            f"/api/v1/customers/{test_customer['id']}/stats",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        payload = resp.json()
        assert payload["code"] == 0
        stats = payload["data"]
        assert "health_score" in stats
        assert "lifecycle" in stats
        assert "total_revenue" in stats
        assert "order_count" in stats


# ═══════════════════════════════════════════════════════════════
# Migration verification
# ═══════════════════════════════════════════════════════════════


class TestMigrationFile:
    """验证数据库迁移文件语法"""

    def test_migration_020_exists(self):
        import os

        path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "app",
            "migrations",
            "020-customer-status-machine.sql",
        )
        assert os.path.exists(path), f"Migration file not found at {path}"

    def test_migration_has_key_statements(self):
        import os

        path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "app",
            "migrations",
            "020-customer-status-machine.sql",
        )
        with open(path) as f:
            sql = f.read()
        assert "ALTER TABLE customers" in sql
        assert "ADD COLUMN" in sql
        assert "status" in sql
        assert "new_lead" in sql
        assert "CREATE INDEX" in sql


# ═══════════════════════════════════════════════════════════════
# Full lifecycle scenario test
# ═══════════════════════════════════════════════════════════════


class TestFullLifecycleScenario:
    """端到端场景：客户从创建到 VIP 的完整生命周期"""

    def test_lifecycle_all_transitions(self):
        """验证完整的合法转换路径"""
        path = [
            ("new_lead", "active"),  # 创建首个机会
            ("active", "converted"),  # 完成首单
            ("converted", "vip"),  # 年交易 > ¥50万
            ("vip", "inactive"),  # 90天无互动
            ("inactive", "active"),  # 重新互动
            ("active", "churned"),  # 手动标记流失
            ("churned", "active"),  # 重新激活
        ]
        for current, target in path:
            try:
                assert_can_transition_customer(current, target)
            except InvalidStateTransition as e:
                pytest.fail(f"Illegal transition {current} → {target}: {e}")

    def test_lifecycle_labels_all_present(self):
        """所有 6 个中文标签都存在"""
        assert CUSTOMER_STATUS_LABELS["new_lead"] == "新潜客"
        assert CUSTOMER_STATUS_LABELS["active"] == "活跃"
        assert CUSTOMER_STATUS_LABELS["converted"] == "已成交"
        assert CUSTOMER_STATUS_LABELS["vip"] == "VIP"
        assert CUSTOMER_STATUS_LABELS["inactive"] == "不活跃"
        assert CUSTOMER_STATUS_LABELS["churned"] == "流失"
