#!/bin/bash
set -e

BACKEND="http://localhost:8080"

# Step 1: Login
LOGIN_RESP=$(curl -s -X POST "$BACKEND/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}')

TOKEN=$(echo "$LOGIN_RESP" | grep -o '"token":"[^"]*"' | cut -d'"' -f4)
echo "Token: ${TOKEN:0:20}..."

# Step 2: Trigger full scan
echo "Triggering watchtower scan..."
SCAN_RESP=$(curl -s -X GET "$BACKEND/api/v1/ai/watchtower/scan?days_back=90" \
  -H "Authorization: Bearer $TOKEN")
echo "Scan response: $SCAN_RESP"

# Step 3: Get unread alerts
echo "Fetching unread alerts..."
ALERTS_RESP=$(curl -s -X GET "$BACKEND/api/v1/customers/alerts?is_read=false&page_size=10" \
  -H "Authorization: Bearer $TOKEN")
echo "Alerts response: $ALERTS_RESP"
