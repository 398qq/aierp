#!/usr/bin/env python3
import json, urllib.request, urllib.parse, sys

BASE = "http://localhost:8080"

def api(method, path, token=None, data=None):
    url = f"{BASE}{path}"
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if data is not None:
        headers["Content-Type"] = "application/json"
        body = json.dumps(data).encode()
    else:
        body = None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())

# Step 1: Login
login = api("POST", "/api/v1/auth/login", data={"username":"admin","password":"admin123"})
token = login["data"]["token"]
print(f"[1] Login OK, token: {token[:15]}...")

# Step 2: Trigger scan
print("[2] Triggering watchtower scan (days_back=90)...")
scan = api("GET", "/api/v1/ai/watchtower/scan?days_back=90", token=token)
print(f"[2] Scan result: {scan}")

# Step 3: Get unread alerts
print("[3] Fetching unread alerts...")
alerts_resp = api("GET", "/api/v1/customers/alerts?is_read=false&page_size=10", token=token)
print(f"[3] Alerts response: {json.dumps(alerts_resp, ensure_ascii=False)}")

alerts = alerts_resp.get("data", {}).get("alerts", []) if alerts_resp.get("data") else []
print(f"    Found {len(alerts)} unread alerts")

if not alerts:
    print("HEARTBEAT_OK")
    sys.exit(0)

# Step 4: Get customer names
customer_ids = list({a.get("customer_id") for a in alerts if a.get("customer_id")})
customer_names = {}
for cid in customer_ids:
    try:
        cust = api("GET", f"/api/v1/customers/{cid}", token=token)
        customer_names[cid] = cust.get("data", {}).get("name", f"Customer({cid})")
    except:
        customer_names[cid] = f"Customer({cid})"

# Step 5: Format and print alerts
for alert in alerts:
    cid = alert.get("customer_id")
    msg = (
        f"🚨 Watchtower 告警\n"
        f"  类型: {alert.get('rule_type','N/A')}\n"
        f"  严重度: {alert.get('severity','N/A')}\n"
        f"  客户: {customer_names.get(cid, cid)}\n"
        f"  摘要: {alert.get('anomaly_summary','N/A')}\n"
    )
    suggestion = alert.get("ai_suggestion")
    if suggestion:
        msg += f"  建议: {suggestion}\n"
    print(f"[ALERT] {json.dumps(alert, ensure_ascii=False)}")
    print(f"[MESSAGE]\n{msg}")

print(f"\nTotal alerts to send: {len(alerts)}")
