#!/bin/bash
# bp-watchdog.sh — Branch Protection watchdog (Stage 19 Day 1, 2026-06-14)
#
# 背景: Stage 18 Day 2 incident (2026-06-14 14:01)
#   - admin-merge.sh 第一次跑超时被 process kill, BP 卡 enforce_admins=false
#   - f89e66f4 retry 只防 transient GitHub 错误, 不防 process kill
#   - 后果: 后续 PR 在弱化 BP 下能直推 master, 风险窗口无限
#
# 解决: 每 5 min cron 一次, 检查 BP, 坏了自动恢复 + 告警
#
# 用法:
#   ./scripts/bp-watchdog.sh                # 检查 + 必要时恢复
#   ./scripts/bp-watchdog.sh --dry-run      # 只检查 + 报告, 不 PUT
#   ./scripts/bp-watchdog.sh --install-cron # 装到 crontab (*/5)
#   ./scripts/bp-watchdog.sh --uninstall-cron
#
# 依赖: ~/.git-credentials 里有 token (用 scripts/setup-credentials.sh setup)
# 告警: $TELEGRAM_BOT_TOKEN (可选, 缺则只写 log)
#       $TELEGRAM_CHAT_ID (默认 8103002093 = 刘经理)
#
# 已知好状态 (2026-06-14 14:02 PR #33 merge 后):
#   - enforce_admins.enabled = true
#   - required_status_checks.contexts = 6 项 (Backend Lint/Test + Frontend Lint/Test/Build/Type)
#   - required_status_checks.strict = true
#   - required_pull_request_reviews.required_approving_review_count = 1
#   - required_pull_request_reviews.require_code_owner_reviews = true
#   - required_linear_history.enabled = true

set -uo pipefail

# ─── Config ───
REPO="398qq/aierp"
BRANCH="master"
CRED_FILE="$HOME/.git-credentials"
LOG_DIR="${LOG_DIR:-$HOME/aierp/logs}"
LOG_FILE="$LOG_DIR/bp-watchdog.log"
BP_BACKUP_DIR="$LOG_DIR/bp-backups"
DEDUP_DIR="$LOG_DIR/.bp-watchdog-dedup"
DEDUP_TTL=3600  # 1h 内同消息不重发

# 期望状态 (master 当前 known-good, 2026-06-14 14:02 后)
EXPECTED_CONTEXTS=(
    "Backend · Lint (ruff)"
    "Backend · Test (pytest)"
    "Frontend · Type check (tsc)"
    "Frontend · Lint (eslint)"
    "Frontend · Test (vitest)"
    "Frontend · Build (vite)"
)
EXPECTED_CONTEXT_COUNT=${#EXPECTED_CONTEXTS[@]}
EXPECTED_ENFORCE_ADMINS=true
EXPECTED_STRICT=true
EXPECTED_APPROVALS=1
EXPECTED_CODE_OWNER_REVIEWS=true
EXPECTED_LINEAR_HISTORY=true

# Telegram
TELEGRAM_CHAT_ID="${TELEGRAM_CHAT_ID:-8103002093}"

# ─── Colors ───
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m'

log()  { echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $*" | tee -a "$LOG_FILE"; }
err()  { echo -e "${RED}[ERR]${NC} $*" | tee -a "$LOG_FILE" >&2; }
ok()   { echo -e "${GREEN}[OK]${NC} $*" | tee -a "$LOG_FILE"; }

mkdir -p "$LOG_DIR" "$BP_BACKUP_DIR" "$DEDUP_DIR"

# ─── Token ───
get_token() {
    if [[ -f "$CRED_FILE" ]] && [[ -s "$CRED_FILE" ]]; then
        grep -oP 'https://(?:x-access-token:)?\K[^@]+' "$CRED_FILE" | tail -1 | sed 's/^.*://'
        return 0
    fi
    return 1
}

# ─── GitHub API helper ───
gh_api() {
    local method="$1"
    local path="$2"
    local data="${3:-}"
    local token
    token="$(get_token)" || { err "No token in $CRED_FILE"; return 1; }

    local args=(-sS --connect-timeout 10 --max-time 30 -X "$method"
                -H "Authorization: token $token"
                -H "Accept: application/vnd.github+json"
                -H "X-GitHub-Api-Version: 2022-11-28"
                -w "\n%{http_code}" "https://api.github.com$path")
    if [[ -n "$data" ]]; then
        args=(-H "Content-Type: application/json" -d "$data" "${args[@]}")
    fi

    local response
    response=$(curl "${args[@]}" 2>/dev/null) || { err "curl failed"; return 1; }
    local http_code
    http_code=$(echo "$response" | tail -1)
    local body
    body=$(echo "$response" | sed '$d')
    echo "$http_code|$body"
}

# ─── Telegram alert ───
telegram_send() {
    local msg="$1"
    if [[ -z "${TELEGRAM_BOT_TOKEN:-}" ]]; then
        log "TELEGRAM_BOT_TOKEN not set, log only: $msg"
        return 0
    fi
    # Dedup
    local key
    key=$(echo "$msg" | md5sum | cut -d' ' -f1)
    local dedup_file="$DEDUP_DIR/$key"
    if [[ -f "$dedup_file" ]]; then
        local age=$(( $(date +%s) - $(stat -c %Y "$dedup_file") ))
        if [[ $age -lt $DEDUP_TTL ]]; then
            log "Dedup hit (age ${age}s < ${DEDUP_TTL}s), skip Telegram: $msg"
            return 0
        fi
    fi
    curl -sS --max-time 10 -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
        -d chat_id="$TELEGRAM_CHAT_ID" \
        -d parse_mode=Markdown \
        -d text="$msg" >/dev/null 2>&1
    touch "$dedup_file"
    ok "Telegram alert sent"
}

# ─── Diff current BP against expected ───
diff_bp() {
    local body="$1"
    local diffs=()

    # Parse (use json.dumps for proper true/false, not Python True/False)
    local enforce_admins
    enforce_admins=$(echo "$body" | python3 -c "import json,sys; d=json.load(sys.stdin); print(json.dumps(d.get('enforce_admins',{}).get('enabled', False)))" 2>/dev/null)
    local strict
    strict=$(echo "$body" | python3 -c "import json,sys; d=json.load(sys.stdin); print(json.dumps(d.get('required_status_checks',{}).get('strict', False)))" 2>/dev/null)
    local approvals
    approvals=$(echo "$body" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('required_pull_request_reviews',{}).get('required_approving_review_count', 0))" 2>/dev/null)
    local code_owner
    code_owner=$(echo "$body" | python3 -c "import json,sys; d=json.load(sys.stdin); print(json.dumps(d.get('required_pull_request_reviews',{}).get('require_code_owner_reviews', False)))" 2>/dev/null)
    local linear
    linear=$(echo "$body" | python3 -c "import json,sys; d=json.load(sys.stdin); print(json.dumps(d.get('required_linear_history',{}).get('enabled', False)))" 2>/dev/null)
    local contexts
    contexts=$(echo "$body" | python3 -c "import json,sys; d=json.load(sys.stdin); print('\n'.join(d.get('required_status_checks',{}).get('contexts', [])))" 2>/dev/null)

    # Check each
    [[ "$enforce_admins" == "$EXPECTED_ENFORCE_ADMINS" ]] || diffs+=("enforce_admins=$enforce_admins (expected $EXPECTED_ENFORCE_ADMINS)")
    [[ "$strict" == "$EXPECTED_STRICT" ]] || diffs+=("strict=$strict (expected $EXPECTED_STRICT)")
    [[ "$approvals" == "$EXPECTED_APPROVALS" ]] || diffs+=("approvals=$approvals (expected $EXPECTED_APPROVALS)")
    [[ "$code_owner" == "$EXPECTED_CODE_OWNER_REVIEWS" ]] || diffs+=("require_code_owner_reviews=$code_owner (expected $EXPECTED_CODE_OWNER_REVIEWS)")
    [[ "$linear" == "$EXPECTED_LINEAR_HISTORY" ]] || diffs+=("required_linear_history=$linear (expected $EXPECTED_LINEAR_HISTORY)")

    local ctx_count
    ctx_count=$(echo "$contexts" | grep -c '^.' || true)
    if [[ $ctx_count -ne $EXPECTED_CONTEXT_COUNT ]]; then
        diffs+=("contexts_count=$ctx_count (expected $EXPECTED_CONTEXT_COUNT)")
    else
        for expected in "${EXPECTED_CONTEXTS[@]}"; do
            if ! echo "$contexts" | grep -Fxq "$expected"; then
                diffs+=("missing context: $expected")
            fi
        done
    fi

    # Print array elements, one per line (caller captures via $())
    if [[ ${#diffs[@]} -eq 0 ]]; then
        return 0
    fi
    printf '%s\n' "${diffs[@]}"
    return 1  # signal that there are diffs
}

# ─── Restore BP from last known-good backup ───
restore_bp() {
    local backup_file
    backup_file=$(ls -t "$BP_BACKUP_DIR"/master-*.json 2>/dev/null | head -1)
    if [[ -z "$backup_file" ]] || [[ ! -f "$backup_file" ]]; then
        err "No backup file in $BP_BACKUP_DIR"
        telegram_send "🔴 *BP watchdog*: 找不到 backup 文件, 无法恢复 BP! 手动修: GET /repos/$REPO/branches/$BRANCH/protection → PUT 回原状"
        return 1
    fi

    log "Restoring BP from $backup_file"
    local payload
    payload=$(python3 -c "
import json
with open('$backup_file') as f:
    bp = json.load(f)
print(json.dumps({
    'required_status_checks': {
        'strict': bp['required_status_checks']['strict'],
        'contexts': bp['required_status_checks']['contexts']
    },
    'required_pull_request_reviews': {
        'dismiss_stale_reviews': bp['required_pull_request_reviews'].get('dismiss_stale_reviews', True),
        'require_code_owner_reviews': bp['required_pull_request_reviews'].get('require_code_owner_reviews', True),
        'require_last_push_approval': bp['required_pull_request_reviews'].get('require_last_push_approval', False),
        'required_approving_review_count': bp['required_pull_request_reviews'].get('required_approving_review_count', 1)
    },
    'restrictions': None,
    'enforce_admins': bp['enforce_admins']['enabled'],
    'required_linear_history': bp['required_linear_history']['enabled'],
    'allow_force_pushes': bp.get('allow_force_pushes', {}).get('enabled', False),
    'allow_deletions': bp.get('allow_deletions', {}).get('enabled', False),
    'block_creations': bp.get('block_creations', {}).get('enabled', False),
    'required_conversation_resolution': bp.get('required_conversation_resolution', {}).get('enabled', True),
    'lock_branch': bp.get('lock_branch', {}).get('enabled', False),
    'allow_fork_syncing': bp.get('allow_fork_syncing', {}).get('enabled', False)
}))")

    local result
    result=$(gh_api PUT "/repos/$REPO/branches/$BRANCH/protection" "$payload")
    local http_code="${result%%|*}"
    local body="${result#*|}"

    if [[ "$http_code" == "200" ]]; then
        ok "BP restored from $backup_file"
        telegram_send "🟢 *BP watchdog*: BP 已自动恢复 from $backup_file

*差异*:
$(echo "$1" | sed 's/^/  - /')

防 Stage 18 Day 2 incident 重演 ✅"
        return 0
    else
        err "BP restore failed: HTTP $http_code, $body"
        telegram_send "🔴 *BP watchdog*: BP restore 失败 HTTP $http_code

```
$body
```

手动修! diff: $1"
        return 1
    fi
}

# ─── Main check ───
check_bp() {
    log "Checking BP for $REPO:$BRANCH..."

    local result
    result=$(gh_api GET "/repos/$REPO/branches/$BRANCH/protection")
    local http_code="${result%%|*}"
    local body="${result#*|}"

    if [[ "$http_code" != "200" ]]; then
        err "GET BP failed: HTTP $http_code"
        [[ "$http_code" == "404" ]] && err "  → Branch protection not configured? Run admin-merge.sh once to bootstrap."
        return 1
    fi

    local diffs
    diffs=$(diff_bp "$body")
    local diff_rc=$?

    if [[ $diff_rc -eq 0 ]]; then
        ok "BP OK (enforce_admins=true, 6 contexts, strict, linear_history)"
        return 0
    else
        warn "BP DIFF detected:"
        echo "$diffs" | sed 's/^/  - /' | tee -a "$LOG_FILE"
        return 2
    fi
}

# ─── Cron install ───
install_cron() {
    local cron_line="*/5 * * * * $PWD/scripts/bp-watchdog.sh >> $LOG_FILE 2>&1"
    local tmp
    tmp=$(mktemp)
    crontab -l 2>/dev/null > "$tmp" || true
    if grep -q "bp-watchdog.sh" "$tmp"; then
        log "Cron already installed"
    else
        echo "$cron_line" >> "$tmp"
        crontab "$tmp"
        ok "Cron installed: $cron_line"
    fi
    rm -f "$tmp"
}

uninstall_cron() {
    local tmp
    tmp=$(mktemp)
    crontab -l 2>/dev/null | grep -v "bp-watchdog.sh" > "$tmp" || true
    crontab "$tmp"
    rm -f "$tmp"
    ok "Cron removed"
}

# ─── Entry point ───
case "${1:-}" in
    --dry-run)
        check_bp
        exit $?
        ;;
    --install-cron)
        install_cron
        exit 0
        ;;
    --uninstall-cron)
        uninstall_cron
        exit 0
        ;;
    "")
        check_bp
        rc=$?
        if [[ $rc -eq 2 ]]; then
            # diffs found → restore
            log "Auto-restoring BP..."
            # Re-fetch diffs
            result=$(gh_api GET "/repos/$REPO/branches/$BRANCH/protection")
            body="${result#*|}"
            diffs=$(diff_bp "$body")
            restore_bp "$diffs"
            exit $?
        fi
        exit $rc
        ;;
    *)
        echo "Usage: $0 [--dry-run|--install-cron|--uninstall-cron]"
        exit 1
        ;;
esac
