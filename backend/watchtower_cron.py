import urllib.request, json, sys

base = "http://localhost:8080"

# Step 1: Login
req = urllib.request.Request(
    f"{base}/api/v1/auth/login",
    data=json.dumps({"username":"admin","password":"admin123"}).encode(),
    headers={"Content-Type":"application/json"}
)
resp = urllib.request.urlopen(req)
data = json.loads(resp.read())
token = data['data']['token']
print(f"TOKEN={token}", file=sys.stderr)

# Step 2: Trigger scan
req2 = urllib.request.Request(
    f"{base}/api/v1/ai/watchtower/scan?days_back=90",
    headers={"Authorization": f"Bearer {token}"}
)
try:
    resp2 = urllib.request.urlopen(req2)
    scan_data = json.loads(resp2.read())
    print(f"SCAN_RESULT={json.dumps(scan_data)}", file=sys.stderr)
except Exception as e:
    print(f"SCAN_ERROR={e}", file=sys.stderr)

# Step 3: Get unread alerts
req3 = urllib.request.Request(
    f"{base}/api/v1/customers/alerts?is_read=false&page_size=10",
    headers={"Authorization": f"Bearer {token}"}
)
resp3 = urllib.request.urlopen(req3)
alerts_data = json.loads(resp3.read())
print(f"ALERTS_COUNT={len(alerts_data.get('data', {}).get('alerts', []))}", file=sys.stderr)
print(json.dumps(alerts_data))