from httpx import AsyncClient


class TestHealthAPI:
    async def test_live_has_request_id_header(self, async_client: AsyncClient):
        resp = await async_client.get(
            "/health/live", headers={"X-Request-ID": "rid-test-123"}
        )
        assert resp.status_code == 200
        assert resp.headers.get("X-Request-ID") == "rid-test-123"
        assert resp.json()["status"] == "ok"
        assert resp.headers.get("X-Content-Type-Options") == "nosniff"
        assert resp.headers.get("X-Frame-Options") == "DENY"
        assert "Content-Security-Policy" in resp.headers

    async def test_health_status_summary(self, async_client: AsyncClient, monkeypatch):
        import app.main as main_module

        async def _db_ok():
            return "ok"

        async def _redis_unavailable():
            return "unavailable"

        async def _ai_ok():
            return "ok"

        monkeypatch.setattr(main_module, "_check_database", _db_ok)
        monkeypatch.setattr(main_module, "_check_redis", _redis_unavailable)
        monkeypatch.setattr(main_module, "_check_ai_service", _ai_ok)

        resp = await async_client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "degraded"
        assert data["checks"] == {
            "database": "ok",
            "redis": "unavailable",
            "ai_service": "ok",
        }
        assert isinstance(data["uptime_seconds"], int)
        assert "version" in data

    async def test_readiness_returns_503_when_db_down(
        self, async_client: AsyncClient, monkeypatch
    ):
        import app.main as main_module

        async def _db_error():
            return "error"

        monkeypatch.setattr(main_module, "_check_database", _db_error)
        resp = await async_client.get("/health/ready")
        assert resp.status_code == 503
        assert resp.json()["status"] == "down"

    async def test_http_exception_is_unified(self, async_client: AsyncClient):
        resp = await async_client.get("/api/v1/products")
        assert resp.status_code == 401
        data = resp.json()
        assert data["code"] == 401
        assert data["data"] is None
        assert isinstance(data.get("request_id"), str)
        assert data.get("msg")

    async def test_validation_exception_is_unified(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        resp = await async_client.post(
            "/api/v1/products", headers=auth_headers, json={"sku": "ONLY-SKU"}
        )
        assert resp.status_code == 422
        data = resp.json()
        assert data["code"] == 422
        assert data["data"] is None
        assert isinstance(data.get("request_id"), str)
        assert "name" in data.get("msg", "")
