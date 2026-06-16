#!/bin/bash
set -e

# Login and get token
LOGIN_RESP=$(curl -s -X POST http://localhost:8080/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}')

TOKEN=$(echo "$LOGIN_RESP" | grep -o '"token": *"[^"]*"' | sed 's/"token": *"\([^"]*\)"/\1/')
echo "Token obtained"

# Trigger full scan
echo "Triggering watchtower scan..."
SCAN_RESP=$(curl -s "http://localhost:8080/api/v1/ai/watchtower/scan?days_back=90" \
  -H "Authorization: Bearer $TOKEN")
echo "Scan response: $SCAN_RESP"

# Get unread alerts
echo "Fetching unread alerts..."
ALERTS_RESP=$(curl -s "http://localhost:8080/api/v1/customers/alerts?is_read=false&page_size=10" \
  -H "Authorization: Bearer $TOKEN")
echo "Alerts response: $ALERTS_RESP"