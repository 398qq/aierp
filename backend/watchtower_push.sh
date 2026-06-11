#!/bin/bash
set -e

BASE="http://localhost:8080/api/v1"
AUTH="{\"username\":\"admin\",\"password\":\"admin123\"}"

# Step 1: Login
LOGIN_RESP=$(curl -s -X POST "${BASE}/auth/login" \
  -H "Content-Type: application/json" \
  -d "$AUTH")

TOKEN=$(echo "$LOGIN_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['token'])")
echo "Token obtained, length=${#TOKEN}"

# Step 2: Trigger scan
echo "Triggering watchtower scan..."
SCAN_RESP=$(curl -s -X GET "${BASE}/ai/watchtower/scan?days_back=90" \
  -H "Authorization: Bearer ${TOKEN}")
echo "Scan response: $SCAN_RESP"

# Step 3: Get unread alerts
echo "Fetching unread alerts..."
ALERTS_RESP=$(curl -s -X GET "${BASE}/customers/alerts?is_read=false&page_size=10" \
  -H "Authorization: Bearer ${TOKEN}")
echo "Alerts response: $ALERTS_RESP"