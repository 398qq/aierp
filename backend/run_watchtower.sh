#!/bin/bash
set -e

# Login
LOGIN_RESP=$(curl -s -X POST http://localhost:8080/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"admin123"}')
TOKEN=$(echo "$LOGIN_RESP" | sed 's/.*"token":"\([^"]*\)".*/\1/')

# Trigger scan
curl -s "http://localhost:8080/api/v1/ai/watchtower/scan?days_back=90" \
  -H "Authorization: Bearer $TOKEN"

echo ""

# Fetch unread alerts
curl -s "http://localhost:8080/api/v1/customers/alerts?is_read=false&page_size=10" \
  -H "Authorization: Bearer $TOKEN"