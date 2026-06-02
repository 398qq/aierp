"""Webhook signature verification — HMAC-SHA256 with timestamp anti-replay.

Standard pattern (used by GitHub, Stripe, Slack):
1. Sender computes HMAC-SHA256 over the request body using a shared secret.
2. Sender includes the signature and a timestamp in the request headers.
3. Receiver re-computes the signature and compares constant-time.
4. Receiver rejects the request if the timestamp is older than
   `MAX_TIMESTAMP_DRIFT_SECONDS` to prevent replay attacks.

Required request headers (case-insensitive):
- `X-AIERP-Signature`: hex-encoded HMAC-SHA256 of `<timestamp>.<body>`
- `X-AIERP-Timestamp`: Unix epoch seconds, must be within 5 minutes of server time

To configure the secret per webhook source, set `IntegrationConfig.api_key_encrypted`
or the env var `WEBHOOK_SECRET_<SOURCE>` (uppercased). For testing, the env var
`WEBHOOK_SECRET` works as a fallback.

Example sender (Python):
    import hmac, hashlib, time
    ts = str(int(time.time()))
    sig = hmac.new(secret.encode(), f"{ts}.{body}".encode(), hashlib.sha256).hexdigest()
    requests.post(url, data=body, headers={
        "X-AIERP-Signature": sig,
        "X-AIERP-Timestamp": ts,
    })
"""

import hashlib
import hmac
import logging
import os
import time
from typing import Optional

from fastapi import Header, HTTPException, Request, status

logger = logging.getLogger(__name__)

SIGNATURE_HEADER = "x-aierp-signature"
TIMESTAMP_HEADER = "x-aierp-timestamp"
MAX_TIMESTAMP_DRIFT_SECONDS = 300  # 5 minutes


def _get_secret(source: str) -> Optional[str]:
    """Resolve the signing secret for a webhook source.

    Lookup order:
    1. Environment variable WEBHOOK_SECRET_<SOURCE_UPPER>
    2. Environment variable WEBHOOK_SECRET (fallback for testing)
    """
    env_key = f"WEBHOOK_SECRET_{source.upper()}"
    secret = os.getenv(env_key) or os.getenv("WEBHOOK_SECRET")
    return secret


def compute_signature(secret: str, timestamp: str, body: bytes) -> str:
    """Compute the canonical signature for a webhook body.

    Format: HMAC-SHA256(secret, f"{timestamp}.{body.decode('utf-8')}")
    Returns: hex-encoded digest.
    """
    if isinstance(body, str):
        body = body.encode("utf-8")
    payload = f"{timestamp}.".encode("utf-8") + body
    return hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()


def verify_signature(
    secret: str,
    signature: str,
    timestamp: str,
    body: bytes,
    now: float | None = None,
) -> bool:
    """Constant-time signature verification with timestamp anti-replay.

    Returns True if signature matches AND timestamp is within drift window.
    """
    if not signature or not timestamp:
        return False

    # Anti-replay: timestamp must be recent
    try:
        ts = float(timestamp)
    except (TypeError, ValueError):
        return False
    if now is None:
        now = time.time()
    if abs(now - ts) > MAX_TIMESTAMP_DRIFT_SECONDS:
        return False

    # Compute expected and compare constant-time
    expected = compute_signature(secret, timestamp, body)
    return hmac.compare_digest(expected, signature)


async def require_webhook_signature(
    request: Request,
    source: str,
    x_aierp_signature: str | None = Header(default=None, alias="X-AIERP-Signature"),
    x_aierp_timestamp: str | None = Header(default=None, alias="X-AIERP-Timestamp"),
) -> bytes:
    """FastAPI dependency that verifies webhook signature.

    Returns the raw request body so the endpoint doesn't need to re-read it.
    Raises 401 on any verification failure.
    """
    secret = _get_secret(source)
    if not secret:
        # No secret configured — fail closed (don't accept unsigned webhooks)
        logger.error(
            "Webhook source '%s' has no secret configured "
            "(set WEBHOOK_SECRET_%s env var)",
            source, source.upper(),
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Webhook source '{source}' is not configured",
        )

    body = await request.body()
    if not verify_signature(secret, x_aierp_signature or "", x_aierp_timestamp or "", body):
        logger.warning(
            "Webhook signature verification failed for source=%s ip=%s",
            source, request.client.host if request.client else "unknown",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature",
        )

    return body
