#!/bin/bash
# ops-alert.sh — 统一运维告警 (Stage 6 Day 2)
#
# Cron: 0 * * * *  /home/ttdiy/aierp/scripts/ops-alert.sh >> /home/ttdiy/aierp/logs/ops-alert.log 2>&1
#
# 检查项：
#   1. Backend 进程存活（/health/live）
#   2. DB 可达（psql ping）
#   3. 磁盘空间 < 80%
#   4. 24 小时内有备份
#   5. Watchtower 有未读 alert
#
# 任何一项失败 → 推 Telegram 告警（用 curl + Telegram Bot API）
# 推送去重：相同消息 1 小时内不重发

set -u

# ============ 配置 ============
TELEGRAM_BOT_TOKEN="${TELEGRAM_BOT_TOKEN:-}"  # 找刘经理要
TELEGRAM_CHAT_ID="${TELEGRAM_CHAT_ID:-8103002093}"  # 刘经理
AIERP_LOGIN_USERNAME="${AIERP_LOGIN_USERNAME:-admin}"
: "${AIERP_LOGIN_PASSWORD:?Set AIERP_LOGIN_PASSWORD before running this script}"
HEALTH_URL="http://localhost:8080/health/live"
BACKUP_DIR="$HOME/date"
LOG_DIR="$HOME/aierp/logs"
DEDUP_DIR="$LOG_DIR/.ops-alert-dedup"
DEDUP_TTL=3600  # 1 小时内同消息不重发
DISK_THRESHOLD=80  # % 警告
BACKUP_MAX_AGE_HOURS=24  # 备份必须 < 24 小时

mkdir -p "$LOG_DIR" "$DEDUP_DIR"

# ============ 工具函数 ============
log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

telegram_send() {
    local msg="$1"
    if [ -z "$TELEGRAM_BOT_TOKEN" ]; then
        log "TELEGRAM_BOT_TOKEN not set, skip: $msg"
        return 0
    fi
    # 去重
    local dedup_key=$(echo -n "$msg" | md5sum | cut -d' ' -f1)
    local dedup_file="$DEDUP_DIR/$dedup_key"
    if [ -f "$dedup_file" ]; then
        local age=$(($(date +%s) - $(stat -c %Y "$dedup_file" 2>/dev/null || echo 0)))
        if [ $age -lt $DEDUP_TTL ]; then
            log "DEDUP: skip (age=${age}s < ${DEDUP_TTL}s): $msg"
            return 0
        fi
    fi
    curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
        -d chat_id="$TELEGRAM_CHAT_ID" \
        -d text="$msg" \
        -d parse_mode=HTML > /dev/null
    touch "$dedup_file"
    log "ALERT sent: $msg"
}

# ============ 检查 ============
ISSUES=()

# 1. Backend 进程
if ! curl -sf --max-time 5 "$HEALTH_URL" >/dev/null 2>&1; then
    ISSUES+=("❌ Backend DOWN: $HEALTH_URL unreachable")
fi

# 2. DB 可达
if ! PGPASSWORD="${PGPASSWORD:-aierp}" psql -h localhost -U "${DB_USER:-aierp}" -d "${DB_NAME:-aierp}" \
    -c "SELECT 1" -tA -q >/dev/null 2>&1; then
    ISSUES+=("❌ PostgreSQL DOWN: psql SELECT 1 failed")
fi

# 3. 磁盘空间
DISK_USED=$(df -P / | tail -1 | awk '{print $5}' | sed 's/%//')
if [ "${DISK_USED:-0}" -ge "$DISK_THRESHOLD" ]; then
    ISSUES+=("⚠️  Disk usage ${DISK_USED}% >= ${DISK_THRESHOLD}%")
fi

# 4. 最新备份
LATEST_BACKUP=$(ls -1t "$BACKUP_DIR"/aierp_*.dump 2>/dev/null | head -1 || echo "")
if [ -z "$LATEST_BACKUP" ]; then
    ISSUES+=("❌ No backup found in $BACKUP_DIR")
else
    LATEST_AGE_HOURS=$(( ($(date +%s) - $(stat -c %Y "$LATEST_BACKUP")) / 3600 ))
    if [ "$LATEST_AGE_HOURS" -ge "$BACKUP_MAX_AGE_HOURS" ]; then
        ISSUES+=("⚠️  Latest backup is ${LATEST_AGE_HOURS}h old (> ${BACKUP_MAX_AGE_HOURS}h): $LATEST_BACKUP")
    fi
fi

# 5. Watchtower 未读告警（如果 backend 还能连上）
if curl -sf --max-time 5 "$HEALTH_URL" >/dev/null 2>&1; then
    LOGIN_PAYLOAD=$(jq -cn \
        --arg username "$AIERP_LOGIN_USERNAME" \
        --arg password "$AIERP_LOGIN_PASSWORD" \
        '{username: $username, password: $password}')
    ALERT_COUNT=$(curl -sf --max-time 5 -X POST "http://localhost:8080/api/v1/auth/login" \
        -H "Content-Type: application/json" \
        -d "$LOGIN_PAYLOAD" 2>/dev/null | \
        python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('data',{}).get('token',''))" 2>/dev/null | \
        xargs -I{} curl -sf --max-time 5 \
            "http://localhost:8080/api/v1/customers/alerts?is_read=false&page_size=1" \
            -H "Authorization: Bearer {}" 2>/dev/null | \
        python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('data',{}).get('total',0))" 2>/dev/null)
    if [ "${ALERT_COUNT:-0}" -gt 0 ]; then
        ISSUES+=("⚠️  Watchtower has ${ALERT_COUNT} unread alerts")
    fi
fi

# ============ 输出 ============
if [ ${#ISSUES[@]} -eq 0 ]; then
    log "✅ All checks passed"
    exit 0
fi

MSG="<b>AIERP Ops Alert</b>%0A%0A"
for issue in "${ISSUES[@]}"; do
    MSG+="• $issue%0A"
done
MSG+="%0A<i>$(date '+%Y-%m-%d %H:%M:%S')</i>"

telegram_send "$MSG"
exit 1
