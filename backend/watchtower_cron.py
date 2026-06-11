#!/usr/bin/env python3
import subprocess, json, sys

# Step 1: Login
r = subprocess.run(
    [
        "curl",
        "-s",
        "-X",
        "POST",
        "http://localhost:8080/api/v1/auth/login",
        "-H",
        "Content-Type: application/json",
        "-d",
        '{"username":"admin","password":"admin123"}',
    ],
    capture_output=True,
    text=True,
)
resp = json.loads(r.stdout)
token = resp["data"]["token"]
print(f"Token: {token[:20]}...", file=sys.stderr)

# Step 2: Trigger scan
r2 = subprocess.run(
    [
        "curl",
        "-s",
        "-X",
        "GET",
        "http://localhost:8080/api/v1/ai/watchtower/scan?days_back=90",
        "-H",
        f"Authorization: Bearer {token}",
    ],
    capture_output=True,
    text=True,
)
print(f"Scan response: {r2.stdout[:800]}", file=sys.stderr)

# Step 3: Get unread alerts
r3 = subprocess.run(
    [
        "curl",
        "-s",
        "-X",
        "GET",
        "http://localhost:8080/api/v1/customers/alerts?is_read=false&page_size=10",
        "-H",
        f"Authorization: Bearer {token}",
    ],
    capture_output=True,
    text=True,
)
alerts_resp = json.loads(r3.stdout)
print(f"Alerts response: {r3.stdout[:1000]}", file=sys.stderr)

alerts = alerts_resp.get("data", {}).get("alerts", [])
print(f"Total unread: {len(alerts)}", file=sys.stderr)

if not alerts:
    print("HEARTBEAT_OK")
    sys.exit(0)

# Step 5: Format and print alerts (we'll send via terminal)
for a in alerts:
    event_id = a.get("event_id")
    rule_type = a.get("rule_type", "")
    severity = a.get("severity", "")
    customer_name = a.get("customer_name", "")
    anomaly_summary = a.get("anomaly_summary", "")
    ai_suggestion = a.get("ai_suggestion", "")
    msg = f"rule_type: {rule_type}\nseverity: {severity}\ncustomer: {customer_name}\nanomaly_summary: {anomaly_summary}"
    if ai_suggestion:
        msg += f"\nai_suggestion: {ai_suggestion}"
    print(f"ALERT:{event_id}|{msg}", file=sys.stderr)
    print(json.dumps({"event_id": event_id, "msg": msg}))

print(f"TOTAL:{len(alerts)}", file=sys.stderr)
