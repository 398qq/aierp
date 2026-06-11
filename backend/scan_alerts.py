#!/usr/bin/env python3
import urllib.request, json

# Login
req = urllib.request.Request(
    "http://localhost:8080/api/v1/auth/login",
    data=json.dumps({"username": "admin", "password": "admin123"}).encode(),
    headers={"Content-Type": "application/json"},
)
resp = urllib.request.urlopen(req)
token = json.loads(resp.read())["data"]["token"]
print("Token obtained")

# Trigger scan
req2 = urllib.request.Request(
    "http://localhost:8080/api/v1/ai/watchtower/scan?days_back=90",
    headers={"Authorization": f"Bearer {token}"},
)
resp2 = urllib.request.urlopen(req2)
scan_result = json.loads(resp2.read())
print("Scan result:", json.dumps(scan_result, ensure_ascii=False))

# Get unread alerts
req3 = urllib.request.Request(
    "http://localhost:8080/api/v1/customers/alerts?is_read=false&page_size=10",
    headers={"Authorization": f"Bearer {token}"},
)
resp3 = urllib.request.urlopen(req3)
alerts_result = json.loads(resp3.read())
print("Alerts result:", json.dumps(alerts_result, ensure_ascii=False))
