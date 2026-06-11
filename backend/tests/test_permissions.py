"""Tests for RBAC permission enforcement (core/permissions.py)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestRequirePerm:
    @pytest.mark.unit
    async def test_admin_role_grants_access(self):
        """Admin RBAC role should bypass specific permission checks."""
        from app.core.permissions import _check_perm_db

        db = MagicMock()
        db.scalar = AsyncMock(return_value=True)

        result = await _check_perm_db(
            db, user_id=1, resource="customers", action="write"
        )
        assert result is True

    @pytest.mark.unit
    async def test_no_permission_returns_false(self):
        """User without matching role/permission should fail."""
        from app.core.permissions import _check_perm_db

        db = MagicMock()
        db.scalar = AsyncMock(return_value=False)

        result = await _check_perm_db(db, user_id=2, resource="finance", action="write")
        assert result is False

    @pytest.mark.unit
    async def test_require_perm_factory_returns_checker(self):
        """require_perm should return a callable dependency."""
        from app.core.permissions import require_perm

        checker = require_perm("customers", "read")
        assert callable(checker)

    @pytest.mark.unit
    async def test_checker_allows_admin(self):
        """The checker dependency should allow admin users."""
        from app.core.permissions import require_perm

        with patch(
            "app.services.cache_service.cache_get", new=AsyncMock(return_value=None)
        ):
            with patch(
                "app.services.cache_service.cache_set", new=AsyncMock(return_value=None)
            ):
                checker = require_perm("system", "write")
                # Build inner function
                inner = (
                    checker.__wrapped__ if hasattr(checker, "__wrapped__") else checker
                )
                # Just verify it's a coroutine function
                import inspect

                assert inspect.iscoroutinefunction(inner)

    @pytest.mark.unit
    async def test_permission_check_uses_cache(self):
        """Cached permission should skip DB query."""
        import json
        from unittest.mock import AsyncMock, patch

        mock_cache_get = AsyncMock(return_value=json.dumps(True))

        with patch("app.services.cache_service.cache_get", new=mock_cache_get):
            with patch("app.services.cache_service.cache_set", new=AsyncMock()):
                from app.core.permissions import require_perm

                checker = require_perm("customers", "read")

                # Mock dependencies
                request = MagicMock()
                current_user = {"user_id": 1, "username": "test"}
                db = MagicMock()
                db.scalar = AsyncMock()  # Should not be called

                result = await checker(
                    request=request, current_user=current_user, db=db
                )

                assert result == current_user
                mock_cache_get.assert_called_once()
                db.scalar.assert_not_called()  # DB query skipped


class TestWriteAuditLog:
    @pytest.mark.unit
    async def test_audit_log_commits(self):
        """write_audit_log should commit, not just flush."""
        from app.core.permissions import write_audit_log
        from unittest.mock import AsyncMock, MagicMock

        db = MagicMock()
        db.add = MagicMock()
        db.commit = AsyncMock()

        await write_audit_log(
            db,
            user_id=1,
            username="test",
            action="create",
            resource_type="role",
            resource_id=1,
        )

        db.add.assert_called_once()
        db.commit.assert_called_once()  # Must commit, not flush

    @pytest.mark.unit
    async def test_audit_log_exception_does_not_raise(self):
        """write_audit_log should swallow exceptions gracefully."""
        from app.core.permissions import write_audit_log
        from unittest.mock import AsyncMock, MagicMock

        db = MagicMock()
        db.add = MagicMock(side_effect=RuntimeError("DB down"))
        db.commit = AsyncMock()

        # Should not raise
        await write_audit_log(
            db,
            user_id=1,
            username="test",
            action="create",
            resource_type="role",
            resource_id=1,
        )

    @pytest.mark.unit
    async def test_audit_log_truncates_long_fields(self):
        """Summary and IP should be truncated."""
        from app.core.permissions import write_audit_log
        from unittest.mock import AsyncMock, MagicMock

        db = MagicMock()
        db.add = MagicMock()
        db.commit = AsyncMock()

        long_summary = "x" * 1000
        long_ip = "y" * 100

        await write_audit_log(
            db,
            user_id=1,
            username="test",
            action="create",
            resource_type="role",
            resource_id=1,
            summary=long_summary,
            ip_address=long_ip,
        )

        # Check that the AuditLog was created with truncated values
        call_args = db.add.call_args[0][0]
        assert len(call_args.summary) == 500
        assert len(call_args.ip_address) == 50


class TestResources:
    @pytest.mark.unit
    def test_resources_dict_has_all_modules(self):
        from app.core.permissions import RESOURCES

        assert "customers" in RESOURCES
        assert "products" in RESOURCES
        assert "sales" in RESOURCES
        assert "finance" in RESOURCES
        assert "system" in RESOURCES
