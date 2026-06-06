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
login = api("POST", "/api/v1/auth/login", data={"username":"admin","password":"admin123"})
token = login["data"]["token"]
print("Logged in, token obtained.")

# Step 2: Trigger scan
print("Triggering watchtower scan...")
scan = api("GET", "/api/v1/ai/watchtower/scan?days_back=90", token=token)
print("Scan result:", scan)

# Step 3: Get unread alerts
print("Fetching unread alerts...")
alerts = api("GET", "/api/v1/customers/alerts?is_read=false&page_size=10", token=token)
print("Alerts response:", json.dumps(alerts, indent=2))

if not alerts.get("data") or not alerts["data"].get("alerts"):
    print("HEARTBEAT_OK")
    sys.exit(0)

alert_list = alerts["data"]["alerts"]
print(f"Found {len(alert_list)} unread alerts")

# Step 5 & 6: Format and collect
messages = []
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
    messages.append((event_id, msg))
    print(msg)
    print("---")

print(f"\nTotal: {len(messages)} alerts to send")
