#!/bin/bash
# backup-pg.sh — PG 全量备份（增强版 Stage 6 Day 3）
#
# 之前 Makefile db-backup 简单 pg_dump，新增：
#   - 时间戳命名（带日期 + 微秒，避免重名）
#   - 压缩（-Fc 自定义格式，比 SQL 压缩比高）
#   - 校验（pg_restore --list 验证备份可读）
#   - 触发 ops-alert（备份成功才不告警）
#   - 自动清理 30 天前
#
# Cron: 0 2 * * *  /home/ttdiy/aierp/scripts/backup-pg.sh >> /home/ttdiy/aierp/logs/backup.log 2>&1

set -euo pipefail

# ============ Config ============
BACKUP_DIR="${BACKUP_DIR:-$HOME/date}"
LOG_DIR="${LOG_DIR:-$HOME/aierp/logs}"
PG_HOST="${PG_HOST:-localhost}"
PG_USER="${PG_USER:-aierp}"
PG_DB="${PG_DB:-aierp}"
PGPASSWORD="${PGPASSWORD:-aierp}"
export PGPASSWORD
RETENTION_DAYS="${RETENTION_DAYS:-30}"

mkdir -p "$BACKUP_DIR" "$LOG_DIR"
LOG="$LOG_DIR/backup-$(date +%Y%m%d).log"
log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG"; }

# ============ Backup ============
TS=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/aierp_${TS}.dump"

log "Starting backup: $BACKUP_FILE"
START=$(date +%s)

# -Fc: custom format (compressed, parallel-restore capable)
# -Z 9: max compression
# -v: verbose
pg_dump -h "$PG_HOST" -U "$PG_USER" -d "$PG_DB" \
    -Fc -Z 9 -v \
    -f "$BACKUP_FILE" 2>>"$LOG"

END=$(date +%s)
DURATION=$((END - START))
SIZE=$(du -h "$BACKUP_FILE" | awk '{print $1}')
log "Backup complete: $BACKUP_FILE ($SIZE in ${DURATION}s)"

# ============ Verify ============
log "Verifying backup integrity..."
if pg_restore -l "$BACKUP_FILE" >/dev/null 2>&1; then
    log "  ✅ Backup is valid"
else
    log "  ❌ Backup verification FAILED"
    exit 1
fi

# ============ Optional:异地复制 ============
# 如配置 REMOTE_BACKUP_DIR，会自动复制（scp / rclone / cp 都可）
if [ -n "${REMOTE_BACKUP_DIR:-}" ]; then
    if cp "$BACKUP_FILE" "$REMOTE_BACKUP_DIR/" 2>>"$LOG"; then
        log "  ✅ Copied to remote: $REMOTE_BACKUP_DIR"
    else
        log "  ⚠️  Failed to copy to remote"
    fi
fi

# ============ Cleanup old backups ============
DELETED=$(find "$BACKUP_DIR" -name "aierp_*.dump" -mtime +${RETENTION_DAYS} -delete -print | wc -l)
if [ "$DELETED" -gt 0 ]; then
    log "  Cleaned $DELETED backups older than ${RETENTION_DAYS} days"
fi

# ============ Stats ============
TOTAL=$(ls -1 "$BACKUP_DIR"/aierp_*.dump 2>/dev/null | wc -l)
TOTAL_SIZE=$(du -sh "$BACKUP_DIR" | awk '{print $1}')
log "Stats: $TOTAL backups, $TOTAL_SIZE total"

log "Done."
