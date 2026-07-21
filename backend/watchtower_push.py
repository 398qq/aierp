import json
import os
import sys

import requests

BASE = "http://localhost:8080/api/v1"
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from lib.erp_auth import get_erp_creds

USERNAME, PASSWORD = get_erp_creds()

# 1. Login
resp = requests.post(
    f"{BASE}/auth/login",
    json={"username": USERNAME, "password": PASSWORD},
    timeout=10,
)
token = resp.json()["data"]["token"]
headers = {"Authorization": f"Bearer {token}"}

# 2. Trigger scan
print("Triggering watchtower scan...")
scan = requests.get(f"{BASE}/ai/watchtower/scan?days_back=90", headers=headers)
print(f"Scan status: {scan.status_code} -> {scan.text[:200]}")

# 3. Get unread alerts
alerts = requests.get(
    f"{BASE}/customers/alerts?is_read=false&page_size=10", headers=headers
)
data = alerts.json()
print(f"Alerts response: {json.dumps(data, ensure_ascii=False)[:500]}")

if data.get("code") != 0:
    print("Error fetching alerts")
    exit(1)

alerts_list = data.get("data", {}).get("alerts", [])
print(f"Found {len(alerts_list)} unread alerts")

if not alerts_list:
    print("HEARTBEAT_OK")
    exit(0)

# 4. Get customer names
customers_resp = requests.get(f"{BASE}/customers/?page_size=100", headers=headers)
customers_data = customers_resp.json()
customer_map = {}
if customers_data.get("code") == 0:
    for c in customers_data.get("data", {}).get("customers", []):
        customer_map[c["id"]] = c.get("name", c.get("company_name", ""))

# 5. Format and send
sent = 0
for alert in alerts_list:
    event_id = alert.get("event_id")
    rule_type = alert.get("rule_type", "")
    severity = alert.get("severity", "")
    customer_id = alert.get("customer_id")
    customer_name = customer_map.get(customer_id, f"Customer#{customer_id}")
    anomaly = alert.get("anomaly_summary", "")
    suggestion = alert.get("ai_suggestion", "")

    msg = "🚨 Watchtower Alert\n\n"
    msg += f"Rule: {rule_type}\n"
    msg += f"Severity: {severity}\n"
    msg += f"Customer: {customer_name}\n"
    msg += f"Summary: {anomaly}\n"
    if suggestion:
        msg += f"Suggestion: {suggestion}"

    print(f"\n--- Alert {event_id} ---")
    print(msg)

    # 6. Send to Telegram
    send_resp = requests.post(
        "http://localhost:8080/api/v1/telegram/send",
        json={"target": "telegram", "message": msg},
    )
    print(f"Telegram send: {send_resp.status_code} -> {send_resp.text[:200]}")

    # 7. Mark as read
    if send_resp.status_code == 200:
        read_resp = requests.post(
            f"{BASE}/customers/alerts/{event_id}/read", headers=headers
        )
        print(f"Mark read: {read_resp.status_code}")
        sent += 1

print(f"\n\nWatchtower 本轮扫描完成，发送了 {sent} 条告警到 Telegram")
