"""Tests for auth security hardening: rate limit + password complexity."""

from unittest.mock import AsyncMock

import pytest
from starlette.requests import Request

from app.api.v1 import auth
from app.api.v1.auth import LoginRequest, _validate_password_complexity


class TestPasswordComplexity:
    def test_short_password_rejected(self):
        assert _validate_password_complexity("Ab1") == "密码至少需要 8 个字符"

    def test_too_long_password_rejected(self):
        assert (
            _validate_password_complexity("Ab1" + "x" * 200)
            == "密码不能超过 128 个字符"
        )

    def test_only_lowercase_rejected(self):
        assert _validate_password_complexity("abcdefgh") is not None
        assert "3 类" in _validate_password_complexity("abcdefgh")

    def test_only_uppercase_rejected(self):
        assert _validate_password_complexity("ABCDEFGH") is not None

    def test_only_digits_rejected(self):
        assert _validate_password_complexity("12345678") is not None

    def test_only_letters_rejected(self):
        # 2 classes (upper+lower) — still rejected
        assert _validate_password_complexity("Abcdefgh") is not None

    def test_letters_and_digits_accepted(self):
        # 3 classes (upper+lower+digits)
        assert _validate_password_complexity("Abcdef12") is None

    def test_letters_and_special_accepted(self):
        # 3 classes (upper+lower+special)
        assert _validate_password_complexity("Abcdef!@") is None

    def test_digits_and_special_accepted(self):
        # 3 classes (lower+digits+special)
        assert _validate_password_complexity("abcdef1!") is None

    def test_strong_password_accepted(self):
        # 4 classes
        assert _validate_password_complexity("Abcdef12!@") is None


class TestLoginRequestSchema:
    """Validate Pydantic input constraints on the login endpoint."""

    def test_username_too_long_rejected(self):
        from app.api.v1.auth import LoginRequest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            LoginRequest(username="a" * 200, password="Abcdef12!")

    def test_empty_username_rejected(self):
        from app.api.v1.auth import LoginRequest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            LoginRequest(username="", password="Abcdef12!")

    def test_short_password_rejected(self):
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            LoginRequest(username="admin", password="")


class TestLoginAvailability:
    async def test_redis_read_failure_does_not_block_valid_login(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        class BrokenRedis:
            async def get(self, key: str):
                raise ConnectionError("redis disconnected")

        user = type(
            "UserStub",
            (),
            {
                "id": 1,
                "username": "admin",
                "password": "hashed",
                "role": "admin",
                "is_active": True,
            },
        )()
        result = type(
            "ResultStub", (), {"scalar_one_or_none": lambda self: user}
        )()
        db = AsyncMock()
        db.execute.return_value = result
        request = Request(
            {
                "type": "http",
                "method": "POST",
                "path": "/api/v1/auth/login",
                "headers": [],
                "client": ("127.0.0.1", 12345),
            }
        )

        monkeypatch.setattr(auth, "_get_r", AsyncMock(return_value=BrokenRedis()))
        monkeypatch.setattr(auth, "verify_password", lambda plain, hashed: True)
        monkeypatch.setattr(auth, "create_access_token", lambda user_id, username: "token")

        response = await auth.login(
            LoginRequest(username="admin", password="valid-password"),
            request,
            db,
        )

        assert response.status_code == 200


class TestChangePasswordRequestSchema:
    def test_weak_new_password_rejected(self):
        from app.api.v1.auth import ChangePasswordRequest
        from pydantic import ValidationError

        with pytest.raises(ValidationError, match="complexity|3"):
            ChangePasswordRequest(
                current_password="OldAbc12!", new_password="weakpass"
            )

    def test_strong_new_password_accepted(self):
        from app.api.v1.auth import ChangePasswordRequest

        req = ChangePasswordRequest(
            current_password="OldAbc12!",
            new_password="NewPwd345!@#",
        )
        assert req.new_password == "NewPwd345!@#"
