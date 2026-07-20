#!/usr/bin/env python3
import json
import os
import sys
import urllib.request

BASE = "http://localhost:8080/api/v1"
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "scripts"))
from lib.erp_auth import get_erp_creds

USERNAME, PASSWORD = get_erp_creds()

# Step 1: Login
req = urllib.request.Request(
    f"{BASE}/auth/login",
    data=json.dumps({"username": USERNAME, "password": PASSWORD}).encode(),
    headers={"Content-Type": "application/json"},
    method="POST",
)
with urllib.request.urlopen(req) as resp:
    login_data = json.loads(resp.read())

token = (login_data.get("data") or {}).get("token")
if not token:
    print("LOGIN FAILED:", login_data)
    sys.exit(1)
print(f"LOGIN OK, token={token[:20]}...")

# Step 2: Trigger scan
req2 = urllib.request.Request(
    f"{BASE}/ai/watchtower/scan?days_back=90",
    headers={"Authorization": f"Bearer {token}"},
    method="GET",
)
with urllib.request.urlopen(req2) as resp:
    scan_data = json.loads(resp.read())
print(f"SCAN: {scan_data}")

# Step 3: Get unread alerts
req3 = urllib.request.Request(
    f"{BASE}/customers/alerts?is_read=false&page_size=10",
    headers={"Authorization": f"Bearer {token}"},
    method="GET",
)
with urllib.request.urlopen(req3) as resp:
    alerts_data = json.loads(resp.read())
print(f"ALERTS: {json.dumps(alerts_data, ensure_ascii=False)}")

alerts = (alerts_data.get("data") or {}).get("list") or []
if not alerts:
    print("HEARTBEAT_OK")
    sys.exit(0)

print(f"Found {len(alerts)} unread alerts")
