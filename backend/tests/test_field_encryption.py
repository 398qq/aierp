"""Tests for field-level encryption (Fernet)."""

import base64


from app.core.field_encryption import (
    EncryptedStr,
    decrypt,
    encrypt,
    mask_for_display,
)


class TestEncryptDecryptRoundTrip:
    def test_basic_round_trip(self):
        original = "13800001234"
        encrypted = encrypt(original)
        decrypted = decrypt(encrypted)
        assert decrypted == original

    def test_ciphertext_differs_from_plaintext(self):
        plain = "secret-token-abc123"
        encrypted = encrypt(plain)
        assert encrypted != plain

    def test_ciphertext_is_urlsafe_base64(self):
        encrypted = encrypt("hello world")
        # Fernet tokens are urlsafe base64 with the prefix
        assert encrypted.startswith("gAAAAA")  # Fernet version 0x80 signature

    def test_chinese_text_round_trip(self):
        text = "北京市朝阳区客户张三"
        assert decrypt(encrypt(text)) == text

    def test_unicode_emoji_round_trip(self):
        text = "客户📞: 138-0000-1234 🎉"
        assert decrypt(encrypt(text)) == text

    def test_long_string_round_trip(self):
        text = "A" * 5000
        assert decrypt(encrypt(text)) == text


class TestEncryptEdgeCases:
    def test_empty_string_returns_empty(self):
        assert encrypt("") == ""
        assert decrypt("") == ""

    def test_unicode_emoji_in_empty_check(self):
        # Single char still encrypts
        assert encrypt("x") != "x"

    def test_decrypt_unencrypted_value_returns_as_is(self):
        """Decryption should be tolerant of legacy plaintext values."""
        # Simulates a row that was saved before encryption was turned on
        assert decrypt("plain-text-not-encrypted") == "plain-text-not-encrypted"

    def test_decrypt_garbage_returns_as_is(self):
        assert decrypt("not-a-valid-fernet-token") == "not-a-valid-fernet-token"

    def test_different_inputs_produce_different_ciphertexts(self):
        # Same plaintext encrypted twice should differ (Fernet adds IV)
        a = encrypt("test")
        b = encrypt("test")
        assert a != b
        # But both decrypt to the same value
        assert decrypt(a) == decrypt(b) == "test"


class TestMaskForDisplay:
    def test_encrypted_value_masked(self):
        encrypted = encrypt("13800001234")
        masked = mask_for_display(encrypted)
        # Should show first/last few chars with ... in between
        assert "..." in masked
        assert "13800001234" not in masked

    def test_short_encrypted_value(self):
        encrypted = encrypt("ab")
        masked = mask_for_display(encrypted)
        # Even short plaintexts encrypt to long ciphertext, so mask shows first/last 4
        assert "..." in masked
        assert len(masked) < len(encrypted)

    def test_plain_text_phone_masked_in_middle(self):
        # If for some reason unencrypted, should still mask
        masked = mask_for_display("13800001234")
        # First 2 + 3 stars + last 2 = 13***34
        assert "13" in masked
        assert "34" in masked
        assert "***" in masked
        # Original digits should NOT be visible
        assert "13800001234" not in masked

    def test_short_plain_text(self):
        assert mask_for_display("ab") == "***"

    def test_empty_value(self):
        assert mask_for_display("") == ""


class TestEncryptedStrType:
    def test_encrypts_on_bind(self):
        enc = EncryptedStr(255)
        result = enc.process_bind_param("13800001234", dialect=None)
        assert result != "13800001234"
        assert result.startswith("gAAAAA")

    def test_decrypts_on_result(self):
        enc = EncryptedStr(255)
        encrypted = encrypt("13800001234")
        result = enc.process_result_value(encrypted, dialect=None)
        assert result == "13800001234"

    def test_handles_none(self):
        enc = EncryptedStr(255)
        assert enc.process_bind_param(None, dialect=None) is None
        assert enc.process_result_value(None, dialect=None) is None

    def test_handles_empty_string(self):
        enc = EncryptedStr(255)
        assert enc.process_bind_param("", dialect=None) == ""
        assert enc.process_result_value("", dialect=None) == ""

    def test_tolerates_unencrypted_value_on_read(self):
        """Migration safety: rows saved before encryption still readable."""
        enc = EncryptedStr(255)
        result = enc.process_result_value("plain-text-legacy", dialect=None)
        assert result == "plain-text-legacy"


class TestKeyDerivation:
    def test_dev_key_deterministic(self):
        # Dev fallback derives from JWT_SECRET, so same JWT_SECRET = same key
        from app.core.field_encryption import _load_or_generate_key
        k1 = _load_or_generate_key()
        k2 = _load_or_generate_key()
        assert k1 == k2
        assert len(k1) == 32  # 256 bits

    def test_explicit_key_takes_precedence(self, monkeypatch):
        # 32 random bytes encoded as urlsafe base64
        test_key = base64.urlsafe_b64encode(b"x" * 32).decode()
        monkeypatch.setenv("FIELD_ENCRYPTION_KEY", test_key)
        # Clear the module-level cache to force re-load
        from app.core import field_encryption as fe
        k = fe._load_or_generate_key()
        assert k == b"x" * 32


class TestKeyLengthValidation:
    def test_invalid_key_length_logs_warning(self, monkeypatch, caplog):
        # Try a too-short key
        monkeypatch.setenv("FIELD_ENCRYPTION_KEY", base64.b64encode(b"short").decode())
        with caplog.at_level("WARNING"):
            from app.core import field_encryption as fe
            fe._load_or_generate_key()
        # Should have fallen back to dev key
        assert any("Invalid FIELD_ENCRYPTION_KEY" in m for m in caplog.messages)
