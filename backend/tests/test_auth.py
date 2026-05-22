import pytest
from httpx import AsyncClient


class TestAuth:
    async def test_login_success(self, async_client: AsyncClient, test_user: dict):
        resp = await async_client.post("/api/v1/auth/login", json={
            "username": test_user["username"],
            "password": test_user["password"],
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 0
        assert data["data"]["token"]
        assert data["data"]["username"] == test_user["username"]

    async def test_login_wrong_password(self, async_client: AsyncClient, test_user: dict):
        resp = await async_client.post("/api/v1/auth/login", json={
            "username": test_user["username"],
            "password": "wrongpassword",
        })
        assert resp.status_code == 401

    async def test_login_nonexistent_user(self, async_client: AsyncClient):
        resp = await async_client.post("/api/v1/auth/login", json={
            "username": "nobody",
            "password": "whatever",
        })
        assert resp.status_code == 401

    async def test_me_authenticated(self, async_client: AsyncClient, auth_headers: dict, test_user: dict):
        resp = await async_client.get("/api/v1/auth/me", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["data"]["username"] == test_user["username"]
        assert data["data"]["user_id"] == test_user["id"]

    async def test_me_no_token(self, async_client: AsyncClient):
        resp = await async_client.get("/api/v1/auth/me")
        assert resp.status_code == 401

    async def test_me_invalid_token(self, async_client: AsyncClient):
        resp = await async_client.get("/api/v1/auth/me", headers={
            "Authorization": "Bearer invalid.token.here",
        })
        assert resp.status_code == 401

    async def test_change_password_success(self, async_client: AsyncClient, auth_headers: dict, test_user: dict, db_session):
        from sqlalchemy import select

        from app.core.security import verify_password
        from app.models.user import User

        resp = await async_client.post(
            "/api/v1/auth/change-password",
            headers=auth_headers,
            json={"current_password": test_user["password"], "new_password": "newpass12345"},
        )

        assert resp.status_code == 200
        assert resp.json()["data"]["changed"] is True

        result = await db_session.execute(select(User).where(User.id == test_user["id"]))
        user = result.scalar_one()
        assert verify_password("newpass12345", user.password) is True
        assert verify_password(test_user["password"], user.password) is False

    async def test_change_password_rejects_wrong_current_password(self, async_client: AsyncClient, auth_headers: dict):
        resp = await async_client.post(
            "/api/v1/auth/change-password",
            headers=auth_headers,
            json={"current_password": "wrongpass", "new_password": "newpass12345"},
        )

        assert resp.status_code == 400
        assert resp.json()["msg"] == "当前密码错误"

    async def test_change_password_requires_auth(self, async_client: AsyncClient):
        resp = await async_client.post(
            "/api/v1/auth/change-password",
            json={"current_password": "testpass123", "new_password": "newpass12345"},
        )

        assert resp.status_code == 401

    @pytest.mark.integration
    async def test_health_endpoint(self, async_client: AsyncClient):
        resp = await async_client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] in {"ok", "degraded"}
