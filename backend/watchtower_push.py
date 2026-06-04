import urllib.request, json, sys

# Step 1: Login
req = urllib.request.Request(
    "http://localhost:8080/api/v1/auth/login",
    data=json.dumps({"username":"admin","password":"admin123"}).encode(),
    headers={"Content-Type":"application/json"},
    method="POST"
)
with urllib.request.urlopen(req) as resp:
    login_data = json.loads(resp.read())

token = login_data["data"]["token"]
print(f"Token obtained: {token[:20]}...", file=sys.stderr)

# Step 2: Trigger scan
req2 = urllib.request.Request(
    "http://localhost:8080/api/v1/ai/watchtower/scan?days_back=90",
    headers={"Authorization": f"Bearer {token}"},
    method="GET"
)
with urllib.request.urlopen(req2) as resp:
    scan_data = json.loads(resp.read())
print(f"Scan response: {scan_data}", file=sys.stderr)

# Step 3: Get unread alerts
req3 = urllib.request.Request(
    "http://localhost:8080/api/v1/customers/alerts?is_read=false&page_size=10",
    headers={"Authorization": f"Bearer {token}"},
    method="GET"
)
with urllib.request.urlopen(req3) as resp:
    alerts_data = json.loads(resp.read())

print(f"Alerts response: {alerts_data}", file=sys.stderr)

alerts = alerts_data.get("data", {}).get("alerts", [])
print(f"Total unread alerts: {len(alerts)}", file=sys.stderr)

if not alerts:
    print("HEARTBEAT_OK")
    sys.exit(0)

# Print each alert as JSON line for parsing
for a in alerts:
    print("ALERT_JSON:" + json.dumps(a))
