#!/bin/bash
set -e

BASE="http://localhost:8080/api/v1"

# Step 1: Login
LOGIN_RESP=$(curl -s -X POST "$BASE/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}')

TOKEN=$(echo "$LOGIN_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['token'])")
echo "Token prefix: ${TOKEN:0:20}..."

# Step 2: Trigger scan
echo "Triggering watchtower scan..."
SCAN_RESP=$(curl -s -X GET "$BASE/ai/watchtower/scan?days_back=90" \
  -H "Authorization: Bearer $TOKEN")
echo "Scan response: $SCAN_RESP"

# Step 3: Get unread alerts
echo "Fetching unread alerts..."
ALERTS_RESP=$(curl -s -X GET "$BASE/customers/alerts?is_read=false&page_size=10" \
  -H "Authorization: Bearer $TOKEN")
echo "Alerts response: $ALERTS_RESP"

# Parse alerts count
ALERTS_COUNT=$(echo "$ALERTS_RESP" | python3 -c "import sys,json; data=json.load(sys.stdin); print(len(data.get('data',{}).get('alerts',[])))")
echo "Unread alerts count: $ALERTS_COUNT"

if [ "$ALERTS_COUNT" = "0" ]; then
    echo "HEARTBEAT_OK"
    exit 0
fi

# Get customer names map
CUSTOMERS=$(curl -s -X GET "$BASE/customers?page_size=1000" \
  -H "Authorization: Bearer $TOKEN")
echo "Customers fetched"

# Process each alert
echo "$ALERTS_RESP" | python3 -c "
import sys, json, subprocess

data = json.load(sys.stdin)
alerts = data.get('data', {}).get('alerts', [])
customers_data = json.loads('''$CUSTOMERS''')
customers_map = {c['id']: c['name'] for c in customers_data.get('data', {}).get('customers', [])}

for alert in alerts:
    event_id = alert['event_id']
    rule_type = alert.get('rule_type', 'unknown')
    severity = alert.get('severity', 'unknown')
    customer_id = alert.get('customer_id')
    customer_name = customers_map.get(customer_id, f'Customer#{customer_id}')
    anomaly = alert.get('anomaly_summary', 'N/A')
    suggestion = alert.get('ai_suggestion', 'N/A')
    
    msg = f'🔔 Watchtower 告警\n'
    msg += f'类型: {rule_type}\n'
    msg += f' severity: {severity}\n'
    msg += f'客户: {customer_name}\n'
    msg += f'异常: {anomaly}\n'
    if suggestion and suggestion != 'N/A':
        msg += f'建议: {suggestion}'
    
    print(f'---ALERT_START---')
    print(msg)
    print(f'---ALERT_END---')
    print(f'EVENT_ID:{event_id}')
" > /tmp/watchtower_alerts.txt

cat /tmp/watchtower_alerts.txt
