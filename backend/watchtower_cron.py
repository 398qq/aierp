import requests, time, json, sys

BASE = "http://localhost:8080"

# Step 1: Login
r = requests.post(f"{BASE}/api/v1/auth/login", json={"username":"admin","password":"admin123"})
if r.status_code != 200:
    print(f"LOGIN FAILED: {r.status_code} {r.text}")
    sys.exit(1)
token = r.json()["data"]["token"]
print(f"Token: {token[:20]}...")

headers = {"Authorization": f"Bearer {token}"}

# Step 2: Trigger scan
print("\nTriggering scan...")
r = requests.get(f"{BASE}/api/v1/ai/watchtower/scan?days_back=90", headers=headers)
print(f"Scan status: {r.status_code} - {r.text[:300]}")
time.sleep(3)

# Step 3: Fetch unread alerts
print("\nFetching unread alerts...")
r = requests.get(f"{BASE}/api/v1/customers/alerts?is_read=false&page_size=10", headers=headers)
data = r.json()
print(f"Status: {r.status_code}, code: {data.get('code')}")
alerts = data.get("data", {}).get("alerts", []) if isinstance(data.get("data"), dict) else data.get("data", [])
print(f"Unread alerts: {len(alerts)}")
print(json.dumps(data, indent=2, ensure_ascii=False))

if not alerts:
    print("HEARTBEAT_OK")
    sys.exit(0)

# Step 4-6: Format and collect messages
messages = []
for alert in alerts:
    event_id = alert.get("event_id")
    rule_type = alert.get("rule_type", "")
    severity = alert.get("severity", "")
    customer_name = alert.get("customer_name", "未知客户")
    anomaly_summary = alert.get("anomaly_summary", "")
    ai_suggestion = alert.get("ai_suggestion", "")

    msg = f"🚨 Watchtower 告警\n\n"
    msg += f"类型: {rule_type}\n"
    msg += f"严重性: {severity}\n"
    msg += f"客户: {customer_name}\n"
    msg += f"摘要: {anomaly_summary}\n"
    if ai_suggestion:
        msg += f"AI 建议: {ai_suggestion}\n"
    messages.append((event_id, msg))
    print(f"\n--- Alert {event_id} ---")
    print(msg)

print(f"\nTotal messages to send: {len(messages)}")