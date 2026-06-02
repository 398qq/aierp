"""Tests for row-level data isolation (record ownership)."""


from app.core.data_isolation import (
    ADMIN_ROLES,
    OWNED_RESOURCES,
    apply_visibility_filter,
    get_data_scope,
    is_admin_or_manager,
)


class TestIsAdminOrManager:
    def test_admin_role_recognized(self):
        user = {"user_id": 1, "role": "admin"}
        assert is_admin_or_manager(user) is True

    def test_manager_role_recognized(self):
        user = {"user_id": 1, "role": "manager"}
        assert is_admin_or_manager(user) is True

    def test_finance_role_recognized(self):
        user = {"user_id": 1, "role": "finance"}
        assert is_admin_or_manager(user) is True

    def test_warehouse_role_recognized(self):
        user = {"user_id": 1, "role": "warehouse"}
        assert is_admin_or_manager(user) is True

    def test_sales_role_not_admin(self):
        user = {"user_id": 2, "role": "sales"}
        assert is_admin_or_manager(user) is False

    def test_admin_in_roles_list(self):
        user = {"user_id": 1, "roles": ["admin", "user"]}
        assert is_admin_or_manager(user) is True

    def test_non_admin_roles_list(self):
        user = {"user_id": 2, "roles": ["sales", "viewer"]}
        assert is_admin_or_manager(user) is False

    def test_empty_roles(self):
        user = {"user_id": 1, "roles": []}
        assert is_admin_or_manager(user) is False

    def test_user_object_with_role_attr(self):
        class FakeUser:
            id = 5
            role = "admin"
            roles = []
        assert is_admin_or_manager(FakeUser()) is True

    def test_user_object_sales_role(self):
        class FakeUser:
            id = 5
            role = "sales"
            roles = []
        assert is_admin_or_manager(FakeUser()) is False


class TestApplyVisibilityFilter:
    def test_owned_resource_admin_no_filter(self):
        from sqlalchemy import select
        from app.models.sales import Opportunity

        stmt = select(Opportunity)
        user = {"user_id": 1, "role": "admin"}
        result = apply_visibility_filter(stmt, user, "opportunities")
        # Should be unchanged (no .where() added by the function itself)
        # Verify the count of where clauses is not increased
        assert len(result._where_criteria) == 0

    def test_owned_resource_sales_rep_adds_filter(self):
        from sqlalchemy import select
        from app.models.sales import Opportunity

        stmt = select(Opportunity)
        user = {"user_id": 5, "role": "sales"}
        result = apply_visibility_filter(stmt, user, "opportunities")
        # Filter should be added
        assert len(result._where_criteria) == 1

    def test_unowned_resource_no_filter(self):
        from sqlalchemy import select
        from app.models.customer import Customer

        stmt = select(Customer)
        user = {"user_id": 5, "role": "sales"}
        result = apply_visibility_filter(stmt, user, "customers")
        # No filter on shared resources
        assert len(result._where_criteria) == 0

    def test_user_with_no_id_returns_empty(self):
        from sqlalchemy import select
        from app.models.sales import Opportunity

        stmt = select(Opportunity)
        user = {"user_id": None, "role": "sales"}
        result = apply_visibility_filter(stmt, user, "opportunities")
        # Where(False) → empty result
        assert len(result._where_criteria) == 1

    def test_sales_rep_sees_own_and_unassigned(self):
        """Sales rep should see records assigned to them OR unassigned ones."""
        from sqlalchemy import select
        from app.models.sales import Opportunity

        stmt = select(Opportunity)
        user = {"user_id": 7, "role": "sales"}
        result = apply_visibility_filter(stmt, user, "opportunities")
        # The filter should be an OR between "assigned to me" and "unassigned"
        assert len(result._where_criteria) == 1

    def test_different_owned_resources_all_filter(self):
        from sqlalchemy import select
        from app.models.sales import Opportunity
        from app.models.customer import CustomerFollowUp
        from app.models.transaction import Ticket

        user = {"user_id": 1, "role": "sales"}
        models = [
            (Opportunity, "opportunities"),
            (CustomerFollowUp, "customer_follow_ups"),
            (Ticket, "tickets"),
        ]
        for model, table in models:
            stmt = select(model)
            result = apply_visibility_filter(stmt, user, table)
            assert len(result._where_criteria) == 1, f"Filter not added for {table}"


class TestGetDataScope:
    def test_admin_scope_is_all(self):
        user = {"user_id": 1, "role": "admin"}
        assert get_data_scope(user) == "all"

    def test_manager_scope_is_all(self):
        user = {"user_id": 1, "role": "manager"}
        assert get_data_scope(user) == "all"

    def test_sales_scope_is_own(self):
        user = {"user_id": 5, "role": "sales"}
        assert get_data_scope(user) == "own_or_unassigned"

    def test_unknown_role_default(self):
        user = {"user_id": 5, "role": "intern"}
        assert get_data_scope(user) == "own_or_unassigned"


class TestOwnedResourcesSet:
    def test_includes_all_expected_resources(self):
        assert "opportunities" in OWNED_RESOURCES
        assert "customer_follow_ups" in OWNED_RESOURCES
        assert "tickets" in OWNED_RESOURCES

    def test_excludes_shared_resources(self):
        assert "customers" not in OWNED_RESOURCES
        assert "products" not in OWNED_RESOURCES
        assert "suppliers" not in OWNED_RESOURCES
        assert "invoices" not in OWNED_RESOURCES
        # Schema gaps — these tables don't have ownership columns yet
        assert "quotations" not in OWNED_RESOURCES
        assert "sales_orders" not in OWNED_RESOURCES
        assert "visits" not in OWNED_RESOURCES
        assert "samples" not in OWNED_RESOURCES

    def test_admin_roles_includes_finance(self):
        assert "finance" in ADMIN_ROLES
        assert "warehouse" in ADMIN_ROLES
        assert "manager" in ADMIN_ROLES
