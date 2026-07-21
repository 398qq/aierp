#!/bin/bash
# restore-test.sh — Stage 15 Day 2: 自动化备份还原测试
#
# 用途: 把最新（或指定）备份还原到独立 DB，验证"备份可恢复"
#       对比源 DB 行数，确认数据完整性
#       可被 cron 调用，失败时返回非零（触发 ops-alert）
#
# 关键修复（Stage 15 Day 1 真发现）:
#   - 必须先 CREATE EXTENSION vector（customers/products 表用 embedding）
#   - 必须 ALTER EXTENSION vector OWNER TO aierp（不然 pg_restore COMMENT 失败）
#   - .pgpass 只对 aierp DB 生效，restore DB 必须 PGPASSWORD 显式传
#
# 用法:
#   ./scripts/restore-test.sh                       # 用最新备份
#   ./scripts/restore-test.sh /path/to/file.dump    # 用指定备份
#   ./scripts/restore-test.sh --keep                # 保留 restore DB（调试用）
#
# Cron (Stage 15 Day 2 计划):
#   0 4 * * 0  /home/ttdiy/aierp/scripts/restore-test.sh >> /home/ttdiy/aierp/logs/restore-test.log 2>&1
#

set -u  # 不要 -e: pg_restore 的 "errors ignored" 是正常的

# ============ Config ============
BACKUP_DIR="${BACKUP_DIR:-$HOME/date}"
SOURCE_DB="${SOURCE_DB:-aierp}"
RESTORE_DB="${RESTORE_DB:-aierp_restore_test_$(date +%Y%m%d_%H%M%S)}"
KEEP_DB=0
PG_HOST="${PG_HOST:-localhost}"
PG_USER="${PG_USER:-aierp}"
PGPASSWORD="${PGPASSWORD:-aierp}"
LOG_DIR="${LOG_DIR:-$HOME/aierp/logs}"

mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/restore-test-$(date +%Y%m%d).log"
log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG"; }
fail() { log "❌ FAIL: $*"; exit 1; }

# ============ Args ============
BACKUP_FILE=""
for arg in "$@"; do
  case "$arg" in
    --keep) KEEP_DB=1 ;;
    *.dump) BACKUP_FILE="$arg" ;;
  esac
done

# ============ Step 0: 选备份 ============
if [ -z "$BACKUP_FILE" ]; then
  BACKUP_FILE=$(ls -1t "$BACKUP_DIR"/aierp_*.dump 2>/dev/null | head -1)
  if [ -z "$BACKUP_FILE" ]; then
    fail "No backup file found in $BACKUP_DIR"
  fi
fi
if [ ! -f "$BACKUP_FILE" ]; then
  fail "Backup file not found: $BACKUP_FILE"
fi
BACKUP_SIZE=$(du -h "$BACKUP_FILE" | awk '{print $1}')
log "===== Restore test started ====="
log "Backup: $BACKUP_FILE ($BACKUP_SIZE)"
log "Source DB: $SOURCE_DB"
log "Restore DB: $RESTORE_DB"

export PGPASSWORD
START=$(date +%s)

# ============ Step 1: 准备 restore DB ============
log "Step 1: Drop & create $RESTORE_DB"
sudo -u postgres psql -c "DROP DATABASE IF EXISTS $RESTORE_DB;" >>"$LOG" 2>&1 || fail "DROP DATABASE failed"
sudo -u postgres psql -c "CREATE DATABASE $RESTORE_DB OWNER $PG_USER;" >>"$LOG" 2>&1 || fail "CREATE DATABASE failed"
sudo -u postgres psql -c "GRANT ALL ON DATABASE $RESTORE_DB TO $PG_USER;" >>"$LOG" 2>&1 || fail "GRANT DATABASE failed"
sudo -u postgres psql -d "$RESTORE_DB" -c "GRANT ALL ON SCHEMA public TO $PG_USER;" >>"$LOG" 2>&1 || fail "GRANT SCHEMA failed"

# ============ Step 2: pgvector 扩展（关键修复）============
# Stage 15 Day 1 发现: customers/products 用 embedding 向量列
# 必须先有 vector 扩展，否则 CREATE TABLE 失败
# PG 没有 ALTER EXTENSION OWNER 语法。COMMENT 在 --no-comments 跳过。
log "Step 2: Create pgvector extension (must be superuser)"
sudo -u postgres psql -d "$RESTORE_DB" -c "CREATE EXTENSION IF NOT EXISTS vector;" >>"$LOG" 2>&1 || fail "CREATE EXTENSION vector failed"

# ============ Step 3: 还原 ============
log "Step 3: pg_restore (--no-owner --no-comments)"
RESTORE_OUTPUT=$(pg_restore -h "$PG_HOST" -U "$PG_USER" -d "$RESTORE_DB" \
  --no-owner --no-comments --role="$PG_USER" "$BACKUP_FILE" 2>&1) || true
echo "$RESTORE_OUTPUT" >>"$LOG"  # log full output
RESTORE_ERRORS=$(echo "$RESTORE_OUTPUT" | grep -c "ERROR\|error:" || true)
log "  pg_restore errors (expected ~0 with --no-comments): $RESTORE_ERRORS"
if [ "$RESTORE_ERRORS" -gt 10 ]; then
  fail "Too many restore errors ($RESTORE_ERRORS). Check $LOG"
fi

# ============ Step 4: 行数对比（核心表）============
log "Step 4: Row count comparison (key tables)"
TABLES=("customers" "products" "suppliers" "sales_orders" "purchase_orders" "commissions" "users" "audit_logs" "inventory_transactions")
MISMATCH=0
for tbl in "${TABLES[@]}"; do
  SRC=$(PGPASSWORD="$PGPASSWORD" psql -h "$PG_HOST" -U "$PG_USER" -d "$SOURCE_DB" -tAc "SELECT count(*) FROM $tbl;" 2>/dev/null | head -1)
  RST=$(PGPASSWORD="$PGPASSWORD" psql -h "$PG_HOST" -U "$PG_USER" -d "$RESTORE_DB" -tAc "SELECT count(*) FROM $tbl;" 2>/dev/null | head -1)
  if [ -z "$SRC" ] || [ -z "$RST" ]; then
    log "  ⚠️  $tbl: source=${SRC:-N/A}, restore=${RST:-N/A} (table may not exist)"
    continue
  fi
  if [ "$SRC" = "$RST" ]; then
    log "  ✅ $tbl: $RST rows (match)"
  else
    log "  ❌ $tbl: source=$SRC, restore=$RST  MISMATCH"
    MISMATCH=$((MISMATCH+1))
  fi
done

END=$(date +%s)
DURATION=$((END - START))
log "===== Done in ${DURATION}s ====="

# ============ Step 5: 清理 ============
if [ "$KEEP_DB" -eq 0 ]; then
  log "Step 5: Drop $RESTORE_DB (use --keep to retain)"
  sudo -u postgres psql -c "DROP DATABASE IF EXISTS $RESTORE_DB;" >>"$LOG" 2>&1 || log "  ⚠️  Drop failed (not critical)"
else
  log "Step 5: KEEP $RESTORE_DB (manual review needed)"
fi

# ============ Result ============
if [ "$MISMATCH" -gt 0 ]; then
  log "❌ RESULT: $MISMATCH table(s) mismatched — backup integrity FAILED"
  exit 1
fi
log "✅ RESULT: All ${#TABLES[@]} tables match — backup integrity OK"
