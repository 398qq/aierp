#!/bin/bash
set -e

BASE="http://localhost:8080"
AIERP_LOGIN_USERNAME="${AIERP_LOGIN_USERNAME:-admin}"
: "${AIERP_LOGIN_PASSWORD:?Set AIERP_LOGIN_PASSWORD before running this script}"
LOGIN_PAYLOAD=$(jq -cn \
  --arg username "$AIERP_LOGIN_USERNAME" \
  --arg password "$AIERP_LOGIN_PASSWORD" \
  '{username: $username, password: $password}')

# Step 1: Login
LOGIN_RESP=$(curl -s -X POST "$BASE/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d "$LOGIN_PAYLOAD")
TOKEN=$(echo "$LOGIN_RESP" | grep -o '"token":"[^"]*"' | cut -d'"' -f4)
echo "TOKEN=${TOKEN:0:20}..."

# Step 2: Trigger full scan
echo "=== Triggering scan ==="
SCAN_RESP=$(curl -s -X GET "$BASE/api/v1/ai/watchtower/scan?days_back=90" \
  -H "Authorization: Bearer $TOKEN")
echo "$SCAN_RESP"

# Step 3: Query unread alerts
echo "=== Querying unread alerts ==="
ALERTS_RESP=$(curl -s -X GET "$BASE/api/v1/customers/alerts?is_read=false&page_size=10" \
  -H "Authorization: Bearer $TOKEN")
echo "$ALERTS_RESP"

# Save alerts for processing
echo "$ALERTS_RESP" > /tmp/alerts_raw.json
echo "alerts saved to /tmp/alerts_raw.json"
