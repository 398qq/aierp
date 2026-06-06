#!/usr/bin/env python3
import urllib.request
import json
import sys

# Step 1: Login
req = urllib.request.Request(
    'http://localhost:8080/api/v1/auth/login',
    data=json.dumps({'username':'admin','password':'admin123'}).encode(),
    headers={'Content-Type':'application/json'}
)
resp = json.loads(urllib.request.urlopen(req).read())
token = resp['data']['token']
print(f"TOKEN={token}", file=sys.stderr)

# Step 2: Trigger scan
req2 = urllib.request.Request(
    'http://localhost:8080/api/v1/ai/watchtower/scan?days_back=90',
    headers={'Authorization': f'Bearer {token}'}
)
try:
    scan_resp = json.loads(urllib.request.urlopen(req2).read())
    print(f"SCAN_OK:{json.dumps(scan_resp)}", file=sys.stderr)
except Exception as e:
    print(f"SCAN_ERR:{e}", file=sys.stderr)

# Step 3: Get unread alerts
req3 = urllib.request.Request(
    'http://localhost:8080/api/v1/customers/alerts?is_read=false&page_size=10',
    headers={'Authorization': f'Bearer {token}'}
)
try:
    alerts_resp = json.loads(urllib.request.urlopen(req3).read())
    print(f"ALERTS:{json.dumps(alerts_resp, ensure_ascii=False)}", file=sys.stderr)
    # Also print to stdout for parsing
    print(json.dumps(alerts_resp, ensure_ascii=False))
except Exception as e:
    print(f"ALERTS_ERR:{e}", file=sys.stderr)