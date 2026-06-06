#!/usr/bin/env python3
import urllib.request, urllib.parse, json, sys

BASE = "http://localhost:8080"

def api(method, path, token=None, data=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    url = BASE + path
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())

# Step 1: Login
login = api("POST", "/api/v1/auth/login", data={"username":"testadmin","password":"admin123"})
token = login["data"]["token"]
print(f"TOKEN_OK", file=sys.stderr)

# Step 2: Trigger scan
print("Triggering watchtower scan...", file=sys.stderr)
try:
    scan = api("GET", "/api/v1/ai/watchtower/scan?days_back=90", token=token)
    print(f"SCAN_OK: {json.dumps(scan)[:200]}", file=sys.stderr)
except Exception as e:
    print(f"SCAN_ERR={e}", file=sys.stderr)

# Step 3: Get unread alerts
print("Fetching unread alerts...", file=sys.stderr)
alerts = api("GET", "/api/v1/customers/alerts?is_read=false&page_size=10", token=token)

if not alerts.get("data") or not alerts["data"].get("alerts"):
    print("HEARTBEAT_OK: no new alerts")
    sys.exit(0)

alert_list = alerts["data"]["alerts"]
print(f"FOUND {len(alert_list)} unread alerts", file=sys.stderr)

# Steps 5-7: Format, send, mark read
from hermes_tools import send_message

results = []
for a in alert_list:
    rule_type = a.get("rule_type","")
    severity = a.get("severity","")
    customer_name = a.get("customer_name","")
    anomaly_summary = a.get("anomaly_summary","")
    ai_suggestion = a.get("ai_suggestion","")
    event_id = a.get("event_id","")

    msg = f"🚨 Watchtower 告警\nrule_type: {rule_type}\nseverity: {severity}\ncustomer: {customer_name}\nanomaly_summary: {anomaly_summary}"
    if ai_suggestion:
        msg += f"\nai_suggestion: {ai_suggestion}"

    # Step 6: Send to Telegram
    try:
        send_message(target="telegram", message=msg)
        print(f"SENT event_id={event_id}", file=sys.stderr)
    except Exception as e:
        print(f"SEND_ERR event_id={event_id} err={e}", file=sys.stderr)
        continue

    # Step 7: Mark as read
    try:
        api("POST", f"/api/v1/customers/alerts/{event_id}/read", token=token)
        print(f"READ_OK event_id={event_id}", file=sys.stderr)
    except Exception as e:
        print(f"READ_ERR event_id={event_id} err={e}", file=sys.stderr)

    results.append(event_id)

print(f"DONE: sent {len(results)} alerts to Telegram")