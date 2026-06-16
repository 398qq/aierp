import pytest
from urllib.parse import urlparse

from app.config import Settings, settings


class TestSettings:
    def test_suite_uses_isolated_security_and_cache_settings(self):
        assert settings.APP_ENV == "test"
        assert len(settings.JWT_SECRET.encode("utf-8")) >= 32
        assert urlparse(settings.REDIS_URL).path not in {"", "/", "/0"}
        assert settings.DATABASE_URL.startswith("sqlite+aiosqlite://")

    def test_cors_origins_supports_comma_separated_string(self):
        cfg = Settings(
            APP_ENV="development",
            CORS_ORIGINS="http://localhost:3002, https://erp.example.com",
        )
        assert cfg.CORS_ORIGINS == ["http://localhost:3002", "https://erp.example.com"]

    def test_production_rejects_wildcard_cors(self):
        with pytest.raises(
            ValueError, match="CORS_ORIGINS cannot contain '\\*' in production"
        ):
            Settings(
                APP_ENV="production",
                DB_PASSWORD="dbpass",
                JWT_SECRET="jwt-secret",
                CORS_ORIGINS="*",
            )

    def test_database_pool_settings_are_configurable(self):
        cfg = Settings(
            DB_POOL_SIZE=30,
            DB_MAX_OVERFLOW=15,
            DB_POOL_RECYCLE_SECONDS=900,
            DB_POOL_PRE_PING=False,
        )
        assert cfg.DB_POOL_SIZE == 30
        assert cfg.DB_MAX_OVERFLOW == 15
        assert cfg.DB_POOL_RECYCLE_SECONDS == 900
        assert cfg.DB_POOL_PRE_PING is False
