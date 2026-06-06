#!/bin/bash
set -e

BASE="http://localhost:8080"
LOGIN=$(curl -s -X POST "$BASE/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}')
TOKEN=$(echo "$LOGIN" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['data']['token'])" 2>/dev/null)
echo "LOGIN_CODE=$(echo "$LOGIN" | python3 -c "import sys,json; print(json.load(sys.stdin)['code'])")"

echo "Triggering scan..."
SCAN=$(curl -s -X GET "$BASE/api/v1/ai/watchtower/scan?days_back=90" \
  -H "Authorization: Bearer $TOKEN")
echo "SCAN=$SCAN"

echo "Fetching unread alerts..."
ALERTS=$(curl -s -X GET "$BASE/api/v1/customers/alerts?is_read=false&page_size=10" \
  -H "Authorization: Bearer $TOKEN")
echo "ALERTS=$ALERTS"
