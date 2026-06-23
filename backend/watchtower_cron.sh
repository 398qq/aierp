#!/bin/bash
set -e

BASE="http://localhost:8080"

# Step 1: Login
LOGIN_RESP=$(curl -s -X POST "$BASE/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}')
TOKEN=$(echo "$LOGIN_RESP" | grep -o '"token":"[^"]*"' | cut -d'"' -f4)
echo "TOKEN=$TOKEN"

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