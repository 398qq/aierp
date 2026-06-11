"""AlertManager webhook receiver (Stage 10 Day 4).

AlertManager POSTs JSON alerts to this service. We re-format them and
forward to Telegram via the Stage 8 telegram_notifier.

Standalone ASGI app on port 9099 — does NOT run inside the main FastAPI
service (separate process, separate concerns). Configure systemd or
supervisord to keep it up.

Payload format from AlertManager:
    {
      "version": "4",
      "status": "firing" | "resolved",
      "alerts": [
        {
          "status": "firing",
          "labels": {"alertname": "...", "severity": "critical", ...},
          "annotations": {"summary": "...", "description": "..."},
          "startsAt": "...",
          "endsAt": "...",
          ...
        }
      ]
    }
"""

from __future__ import annotations

import json
import logging
import os

from fastapi import FastAPI, HTTPException, Request

logger = logging.getLogger(__name__)

app = FastAPI(title="AIERP AlertManager Webhook", version="1.0")


def _format_alert(alert: dict) -> str:
    """Convert an AlertManager alert dict into a Telegram message."""
    labels = alert.get("labels", {})
    annotations = alert.get("annotations", {})
    status = alert.get("status", "firing")

    name = labels.get("alertname", "unknown")
    severity = labels.get("severity", "info")
    service = labels.get("service", "aierp")

    if status == "resolved":
        emoji = "✅"
        action = "RESOLVED"
    elif severity == "critical":
        emoji = "🚨"
        action = "FIRING (CRITICAL)"
    elif severity == "warning":
        emoji = "⚠️"
        action = "FIRING"
    else:
        emoji = "ℹ️"
        action = "INFO"

    lines = [
        f"{emoji} <b>{action}: {name}</b>",
        f"Service: {service}",
        f"Severity: {severity}",
    ]
    summary = annotations.get("summary", "")
    if summary:
        lines.append(f"\n<b>{summary}</b>")
    description = annotations.get("description", "")
    if description:
        lines.append(f"\n{description}")
    starts_at = alert.get("startsAt", "")
    if starts_at:
        lines.append(f"\n<i>Started: {starts_at}</i>")
    ends_at = alert.get("endsAt", "")
    if ends_at and status == "resolved":
        lines.append(f"<i>Ended: {ends_at}</i>")
    return "\n".join(lines)


@app.post("/alert")
async def alert_endpoint(request: Request):
    """Receive AlertManager webhook and forward to Telegram."""
    body = await request.body()
    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"invalid JSON: {exc}")

    alerts = payload.get("alerts", [])
    if not alerts:
        return {"ok": True, "forwarded": 0, "note": "no alerts in payload"}

    # Lazy import so the receiver can start even if telegram_notifier is broken
    try:
        from app.services.telegram_notifier import send_message
    except Exception as exc:  # noqa: BLE001
        logger.error("telegram_notifier import failed: %s", exc)
        raise HTTPException(status_code=500, detail="telegram notifier unavailable")

    forwarded = 0
    failures = 0
    for alert in alerts:
        try:
            msg = _format_alert(alert)
            ok = await send_message(msg)
            if ok:
                forwarded += 1
            else:
                failures += 1
        except Exception as exc:  # noqa: BLE001
            logger.exception("alert forward failed: %s", exc)
            failures += 1

    return {"ok": True, "forwarded": forwarded, "failures": failures}


@app.post("/alert-critical")
async def alert_critical_endpoint(request: Request):
    """Same as /alert but always uses critical-style formatting.

    Wired in alertmanager.yml for severity=critical alerts.
    """
    # For now identical to /alert — the severity emoji is already set
    # by _format_alert() based on the alert's severity label.
    return await alert_endpoint(request)


@app.get("/health")
async def health():
    """Health check for the receiver itself."""
    return {
        "ok": True,
        "service": "alertmanager-webhook",
        "telegram_configured": bool(os.environ.get("TELEGRAM_BOT_TOKEN")),
    }
