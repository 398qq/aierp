"""Tests for auth security hardening: rate limit + password complexity."""

import pytest

from app.api.v1.auth import _validate_password_complexity


class TestPasswordComplexity:
    def test_short_password_rejected(self):
        assert _validate_password_complexity("Ab1") == "密码至少需要 8 个字符"

    def test_too_long_password_rejected(self):
        assert _validate_password_complexity("Ab1" + "x" * 200) == "密码不能超过 128 个字符"

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
        from app.api.v1.auth import LoginRequest
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            LoginRequest(username="admin", password="")


class TestChangePasswordRequestSchema:
    def test_weak_new_password_rejected(self):
        from app.api.v1.auth import ChangePasswordRequest
        from pydantic import ValidationError
        with pytest.raises(ValidationError, match="complexity|3"):
            ChangePasswordRequest(current_password="OldAbc12!", new_password="weak")

    def test_strong_new_password_accepted(self):
        from app.api.v1.auth import ChangePasswordRequest
        req = ChangePasswordRequest(
            current_password="OldAbc12!",
            new_password="NewPwd345!@#",
        )
        assert req.new_password == "NewPwd345!@#"
