import pytest

from app.config import Settings


class TestSettings:
    def test_cors_origins_stored_as_raw_string(self):
        cfg = Settings(
            APP_ENV="development",
            CORS_ORIGINS="http://localhost:3002,https://erp.example.com",
        )
        assert isinstance(cfg.CORS_ORIGINS, str)
        assert "http://localhost:3002" in cfg.CORS_ORIGINS
        assert "https://erp.example.com" in cfg.CORS_ORIGINS

    def test_cors_origins_empty_string(self):
        cfg = Settings(APP_ENV="development", CORS_ORIGINS="")
        assert cfg.CORS_ORIGINS == ""

    def test_cors_origins_single_origin(self):
        cfg = Settings(APP_ENV="development", CORS_ORIGINS="https://myapp.com")
        assert cfg.CORS_ORIGINS == "https://myapp.com"

    def test_cors_origins_default_value(self):
        cfg = Settings(APP_ENV="development")
        assert "localhost:3002" in cfg.CORS_ORIGINS

    def test_cors_origins_with_whitespace_preserved_as_is(self):
        cfg = Settings(
            APP_ENV="development",
            CORS_ORIGINS="http://a.com, https://b.com",
        )
        assert cfg.CORS_ORIGINS == "http://a.com, https://b.com"

    def test_production_accepts_non_wildcard_cors(self):
        cfg = Settings(
            APP_ENV="production",
            DB_PASSWORD="dbpass",
            JWT_SECRET="jwt-secret",
            CORS_ORIGINS="https://erp.example.com",
        )
        assert cfg.CORS_ORIGINS == "https://erp.example.com"

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
