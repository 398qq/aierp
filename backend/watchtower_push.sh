#!/bin/bash
# Watchtower — 监测告警推送脚本
# 修复: JSON 通过临时文件传递，避免 shell 变量注入 Python 代码
set -euo pipefail

BASE="http://localhost:8080/api/v1"
ALERTS_FILE="/tmp/watchtower_alerts.json"
CUSTOMERS_FILE="/tmp/watchtower_customers.json"
LOGIN_FILE="/tmp/watchtower_login.json"
AIERP_LOGIN_USERNAME="${AIERP_LOGIN_USERNAME:-admin}"
: "${AIERP_LOGIN_PASSWORD:?Set AIERP_LOGIN_PASSWORD before running this script}"
LOGIN_PAYLOAD=$(jq -cn \
  --arg username "$AIERP_LOGIN_USERNAME" \
  --arg password "$AIERP_LOGIN_PASSWORD" \
  '{username: $username, password: $password}')
trap 'rm -f "$ALERTS_FILE" "$CUSTOMERS_FILE" "$LOGIN_FILE"' EXIT

# ── Login ──
LOGIN_RESP=$(curl -sS -X POST "$BASE/auth/login" \
  -H "Content-Type: application/json" \
  -d "$LOGIN_PAYLOAD")
printf '%s' "$LOGIN_RESP" > "$LOGIN_FILE"
TOKEN=$(python3 -c "import json; d=json.load(open('$LOGIN_FILE')); print(d['data']['token'])")

# ── Trigger scan ──
echo "Triggering watchtower scan..."
curl -sS -X GET "$BASE/ai/watchtower/scan?days_back=90" \
  -H "Authorization: Bearer $TOKEN" > /dev/null
echo "Scan done"

# ── Fetch alerts to file ──
curl -sS -X GET "$BASE/customers/alerts?is_read=false&page_size=20" \
  -H "Authorization: Bearer $TOKEN" > "$ALERTS_FILE"

ALERTS_COUNT=$(python3 -c "
import json
with open('$ALERTS_FILE') as f:
    d = json.load(f)
print(len(d.get('data',{}).get('alerts',[])))
")
echo "Unread alerts: $ALERTS_COUNT"

if [ "$ALERTS_COUNT" = "0" ]; then
    echo "HEARTBEAT_OK"
    exit 0
fi

# ── Fetch customers to file ──
curl -sS -X GET "$BASE/customers?page_size=200" \
  -H "Authorization: Bearer $TOKEN" > "$CUSTOMERS_FILE"

# ── Process alerts ──
python3 << PYEOF
import json

with open("$ALERTS_FILE") as f:
    alerts_data = json.load(f)
with open("$CUSTOMERS_FILE") as f:
    customers_data = json.load(f)

alerts = alerts_data.get("data", {}).get("alerts", [])
customers_list = customers_data.get("data", {}).get("list", [])
cust_map = {c["id"]: c["name"] for c in customers_list}

for alert in alerts:
    eid = alert.get("event_id", "?")
    rule = alert.get("rule_type", "unknown")
    sev = alert.get("severity", "unknown")
    cid = alert.get("customer_id")
    name = cust_map.get(cid, f"Customer#{cid}")
    anomaly = alert.get("anomaly_summary", "N/A")
    suggestion = alert.get("ai_suggestion", "")

    print("---ALERT_START---")
    print(f"类型: {rule}  严重度: {sev}")
    print(f"客户: {name}")
    print(f"异常: {anomaly}")
    if suggestion and suggestion != "N/A":
        print(f"建议: {suggestion}")
    print("---ALERT_END---")
    print(f"EVENT_ID:{eid}")
PYEOF
