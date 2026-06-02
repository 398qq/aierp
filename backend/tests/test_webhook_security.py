"""Tests for webhook signature verification (HMAC-SHA256)."""

import time
from unittest.mock import patch


from app.core.webhook_security import (
    MAX_TIMESTAMP_DRIFT_SECONDS,
    compute_signature,
    verify_signature,
)


SECRET = "test-webhook-secret-12345"


class TestComputeSignature:
    def test_produces_hex_64_chars(self):
        sig = compute_signature(SECRET, "1234567890", b'{"event": "test"}')
        assert len(sig) == 64
        assert all(c in "0123456789abcdef" for c in sig)

    def test_same_inputs_produce_same_output(self):
        a = compute_signature(SECRET, "100", b"body")
        b = compute_signature(SECRET, "100", b"body")
        assert a == b

    def test_different_timestamps_produce_different_output(self):
        a = compute_signature(SECRET, "100", b"body")
        b = compute_signature(SECRET, "101", b"body")
        assert a != b

    def test_different_bodies_produce_different_output(self):
        a = compute_signature(SECRET, "100", b"body1")
        b = compute_signature(SECRET, "100", b"body2")
        assert a != b

    def test_accepts_string_body(self):
        a = compute_signature(SECRET, "100", "string body")
        b = compute_signature(SECRET, "100", b"string body")
        assert a == b

    def test_different_secrets_produce_different_output(self):
        a = compute_signature("secret1", "100", b"body")
        b = compute_signature("secret2", "100", b"body")
        assert a != b


class TestVerifySignature:
    def test_valid_signature_within_window(self):
        ts = str(int(time.time()))
        body = b'{"event": "test"}'
        sig = compute_signature(SECRET, ts, body)
        assert verify_signature(SECRET, sig, ts, body) is True

    def test_rejects_missing_signature(self):
        ts = str(int(time.time()))
        assert verify_signature(SECRET, "", ts, b"body") is False
        assert verify_signature(SECRET, None, ts, b"body") is False

    def test_rejects_missing_timestamp(self):
        sig = compute_signature(SECRET, "100", b"body")
        assert verify_signature(SECRET, sig, "", b"body") is False
        assert verify_signature(SECRET, sig, None, b"body") is False

    def test_rejects_tampered_body(self):
        ts = str(int(time.time()))
        sig = compute_signature(SECRET, ts, b"original body")
        assert verify_signature(SECRET, sig, ts, b"tampered body") is False

    def test_rejects_tampered_signature(self):
        ts = str(int(time.time()))
        sig = compute_signature(SECRET, ts, b"body")
        tampered = sig[:-2] + ("ff" if sig[-2:] != "ff" else "00")
        assert verify_signature(SECRET, tampered, ts, b"body") is False

    def test_rejects_old_timestamp_replay(self):
        """A signature older than MAX_TIMESTAMP_DRIFT_SECONDS should fail."""
        old_ts = str(int(time.time()) - MAX_TIMESTAMP_DRIFT_SECONDS - 60)
        body = b"body"
        sig = compute_signature(SECRET, old_ts, body)
        assert verify_signature(SECRET, sig, old_ts, body) is False

    def test_rejects_future_timestamp(self):
        future_ts = str(int(time.time()) + 600)  # 10 min in future
        body = b"body"
        sig = compute_signature(SECRET, future_ts, body)
        assert verify_signature(SECRET, sig, future_ts, body) is False

    def test_rejects_non_numeric_timestamp(self):
        assert verify_signature(SECRET, "valid_sig", "not-a-number", b"body") is False

    def test_handles_unicode_body(self):
        ts = str(int(time.time()))
        body = '{"name": "测试"}'.encode("utf-8")
        sig = compute_signature(SECRET, ts, body)
        assert verify_signature(SECRET, sig, ts, body) is True


class TestSignatureTimingSafety:
    """Verify the verify function uses constant-time comparison."""

    def test_compare_digest_used(self):
        """We rely on hmac.compare_digest; spot-check by patching."""
        with patch("app.core.webhook_security.hmac.compare_digest") as mock:
            mock.return_value = True
            ts = str(int(time.time()))
            result = verify_signature(SECRET, "any", ts, b"any")
            assert result is True
            assert mock.called


class TestSignatureEndToEnd:
    """Simulate the full sender-receiver round trip."""

    def test_round_trip(self):
        secret = "shh-its-a-secret"
        body = '{"order_id": 123, "status": "paid"}'.encode("utf-8")
        ts = str(int(time.time()))

        # Sender side
        sig = compute_signature(secret, ts, body)

        # Receiver side
        assert verify_signature(secret, sig, ts, body) is True

    def test_5_minute_drift_accepted(self):
        secret = "shh"
        body = b"body"
        ts = str(int(time.time()) - 290)  # 4:50 in past — within window
        sig = compute_signature(secret, ts, body)
        assert verify_signature(secret, sig, ts, body) is True

    def test_6_minute_drift_rejected(self):
        secret = "shh"
        body = b"body"
        ts = str(int(time.time()) - 360)  # 6 min in past
        sig = compute_signature(secret, ts, body)
        assert verify_signature(secret, sig, ts, body) is False
