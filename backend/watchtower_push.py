#!/usr/bin/env python3
import urllib.request, urllib.error, json, sys

BASE = "http://localhost:8080"

def api(method, path, token=None, data=None):
    url = f"{BASE}{path}"
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, method=method, data=body)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())

# Step 1: login
login = api("POST", "/api/v1/auth/login", data={"username":"admin","password":"admin123"})
print("Login:", login.get("msg"))
token = login["data"]["token"]
print("Token obtained")

# Step 2: trigger scan
print("=== Triggering watchtower scan ===")
scan = api("GET", "/api/v1/ai/watchtower/scan?days_back=90", token=token)
print("Scan result:", json.dumps(scan, ensure_ascii=False))

# Step 3: get unread alerts
print("=== Fetching unread alerts ===")
alerts = api("GET", "/api/v1/customers/alerts?is_read=false&page_size=10", token=token)
print("Alerts response:", json.dumps(alerts, ensure_ascii=False))

alerts_list = alerts.get("data", {}).get("items", [])
print(f"Unread alerts count: {len(alerts_list)}")

if not alerts_list:
    print("HEARTBEAT_OK")
    sys.exit(0)

# Step 5 & 6: format and send each alert
sent = 0
for alert in alerts_list:
    event_id = alert.get("event_id") or alert.get("id")
    rule_type = alert.get("rule_type", "unknown")
    severity = alert.get("severity", "unknown")
    customer_name = alert.get("customer_name", alert.get("customer", "未知客户"))
    anomaly_summary = alert.get("anomaly_summary", "无摘要")
    ai_suggestion = alert.get("ai_suggestion") or "无建议"

    msg = (
        f"🚨 Watchtower 告警\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📌 类型: {rule_type}\n"
        f"⚠️  等级: {severity}\n"
        f"👤 客户: {customer_name}\n"
        f"📋 摘要: {anomaly_summary}\n"
        f"💡 建议: {ai_suggestion}"
    )
    print(f"\n--- Alert {event_id} ---")
    print(msg)

    # Step 7: mark as read
    read = api("POST", f"/api/v1/customers/alerts/{event_id}/read", token=token)
    print(f"Mark read: {read.get('msg', read)}")
    sent += 1

print(f"\n=== Done: sent {sent} alerts ===")