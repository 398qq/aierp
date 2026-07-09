import urllib.request, json, sys

BASE = "http://localhost:8080"

# Step 1: login
req = urllib.request.Request(
    f"{BASE}/api/v1/auth/login",
    data=json.dumps({"username":"admin","password":"admin123"}).encode(),
    headers={"Content-Type":"application/json"},
    method="POST"
)
with urllib.request.urlopen(req) as r:
    login_data = json.loads(r.read())
token = login_data["data"]["token"]
print(f"LOGIN OK, token={token[:20]}...")

# Step 2: trigger scan
req2 = urllib.request.Request(
    f"{BASE}/api/v1/ai/watchtower/scan?days_back=90",
    headers={"Authorization": f"Bearer {token}"},
    method="GET"
)
with urllib.request.urlopen(req2) as r:
    scan_data = json.loads(r.read())
print(f"SCAN: {json.dumps(scan_data, ensure_ascii=False)}")

# Step 3: fetch unread alerts
req3 = urllib.request.Request(
    f"{BASE}/api/v1/customers/alerts?is_read=false&page_size=10",
    headers={"Authorization": f"Bearer {token}"},
    method="GET"
)
with urllib.request.urlopen(req3) as r:
    alerts_data = json.loads(r.read())
print(f"ALERTS: {json.dumps(alerts_data, ensure_ascii=False)}")

# Step 4: check if empty
alerts = alerts_data.get("data", {}).get("alerts", [])
if not alerts:
    print("HEARTBEAT_OK")
    sys.exit(0)

print(f"Found {len(alerts)} unread alerts")