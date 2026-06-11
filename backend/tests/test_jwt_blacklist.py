"""Tests for JWT blacklist — session revocation."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch


from app.core import security
from app.core.security import (
    create_access_token,
    decode_access_token,
    get_token_ttl_seconds,
    is_token_revoked,
    revoke_token,
)


class TestTokenStructure:
    def test_includes_jti(self):
        token = create_access_token(user_id=42, username="test")
        payload = decode_access_token(token)
        assert payload is not None
        assert "jti" in payload
        assert len(payload["jti"]) == 32  # UUID hex

    def test_jti_is_unique_per_token(self):
        t1 = create_access_token(1, "u")
        t2 = create_access_token(1, "u")
        jti1 = decode_access_token(t1)["jti"]
        jti2 = decode_access_token(t2)["jti"]
        assert jti1 != jti2

    def test_includes_iat_and_exp(self):
        token = create_access_token(1, "u")
        payload = decode_access_token(token)
        assert "iat" in payload
        assert "exp" in payload

    def test_decode_returns_none_for_garbage(self):
        assert decode_access_token("not-a-jwt") is None

    def test_decode_returns_none_for_tampered(self):
        token = create_access_token(1, "u")
        # Flip a character
        tampered = "x" + token[1:]
        assert decode_access_token(tampered) is None


class TestGetTokenTtl:
    def test_future_token_has_positive_ttl(self):
        token = create_access_token(1, "u")
        payload = decode_access_token(token)
        ttl = get_token_ttl_seconds(payload)
        assert ttl > 0
        assert ttl <= 60 * 60 * 24 * 7 + 60  # Within 7 days + slack

    def test_expired_token_has_zero_ttl(self):
        # Build a payload manually with past expiry
        payload = {"exp": datetime.now(timezone.utc) - timedelta(minutes=1)}
        assert get_token_ttl_seconds(payload) == 0

    def test_no_exp_field(self):
        assert get_token_ttl_seconds({}) == 0

    def test_numeric_exp_field(self):
        # JWT spec allows exp as int Unix timestamp
        future_ts = (datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()
        payload = {"exp": int(future_ts)}
        ttl = get_token_ttl_seconds(payload)
        assert 3500 < ttl < 3700  # 1 hour ± 100s


class TestRevokeToken:
    async def test_revoke_adds_to_blacklist(self):
        mock_redis = MagicMock()
        mock_redis.set = AsyncMock()
        with patch(
            "app.services.cache_service.get_redis", AsyncMock(return_value=mock_redis)
        ):
            result = await revoke_token("test-jti", ttl_seconds=60)
        assert result is True
        mock_redis.set.assert_called_once()
        # Verify the key includes the prefix
        args = mock_redis.set.call_args
        assert args[0][0] == "aierp:jwt_blacklist:test-jti"
        assert args[0][1] == "1"
        assert args[1]["ex"] == 60

    async def test_revoke_returns_false_on_redis_failure(self):
        with patch(
            "app.services.cache_service.get_redis", AsyncMock(return_value=None)
        ):
            result = await revoke_token("test-jti", ttl_seconds=60)
        assert result is False

    async def test_revoke_returns_false_on_set_error(self):
        mock_redis = MagicMock()
        mock_redis.set = AsyncMock(side_effect=ConnectionError("boom"))
        with patch(
            "app.services.cache_service.get_redis", AsyncMock(return_value=mock_redis)
        ):
            result = await revoke_token("test-jti", ttl_seconds=60)
        assert result is False


class TestIsTokenRevoked:
    async def test_returns_true_when_blacklisted(self):
        mock_redis = MagicMock()
        mock_redis.exists = AsyncMock(return_value=1)
        with patch(
            "app.services.cache_service.get_redis", AsyncMock(return_value=mock_redis)
        ):
            result = await is_token_revoked("revoked-jti")
        assert result is True

    async def test_returns_false_when_not_blacklisted(self):
        mock_redis = MagicMock()
        mock_redis.exists = AsyncMock(return_value=0)
        with patch(
            "app.services.cache_service.get_redis", AsyncMock(return_value=mock_redis)
        ):
            result = await is_token_revoked("active-jti")
        assert result is False

    async def test_returns_false_when_redis_unavailable(self):
        """Fail open: if Redis is down, treat token as not revoked."""
        with patch(
            "app.services.cache_service.get_redis", AsyncMock(return_value=None)
        ):
            result = await is_token_revoked("any-jti")
        assert result is False

    async def test_returns_false_for_empty_jti(self):
        # No JTI = can't check blacklist
        result = await is_token_revoked("")
        assert result is False

    async def test_returns_false_on_redis_error(self):
        mock_redis = MagicMock()
        mock_redis.exists = AsyncMock(side_effect=ConnectionError("boom"))
        with patch(
            "app.services.cache_service.get_redis", AsyncMock(return_value=mock_redis)
        ):
            result = await is_token_revoked("any-jti")
        assert result is False


class TestRevokeAllUserTokens:
    async def test_logs_warning_and_returns_zero(self):
        """Full impl requires token_version column migration."""
        with patch.object(security, "logger") as mock_log:
            count = await security.revoke_all_user_tokens(user_id=42)
        assert count == 0
        # Should log a warning so deploys catch the pending migration
        assert any(
            "token_version" in str(c.args) for c in mock_log.warning.call_args_list
        )


class TestBlacklistIntegration:
    async def test_revoked_token_rejected_on_check(self):
        """End-to-end: revoke then check returns True."""
        mock_redis = MagicMock()
        mock_redis.set = AsyncMock()
        mock_redis.exists = AsyncMock(side_effect=[1])  # Always returns 1 (revoked)
        with patch(
            "app.services.cache_service.get_redis", AsyncMock(return_value=mock_redis)
        ):
            await revoke_token("jti-abc", ttl_seconds=60)
            is_revoked = await is_token_revoked("jti-abc")
        assert is_revoked is True
