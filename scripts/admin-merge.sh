#!/bin/bash
# admin-merge.sh — Admin override 流程 (Stage 17 Day 1 引入)
#
# 问题: 单人 repo + Branch Protection (enforce_admins=True + require_code_owner_reviews=True)
#       → admin 用户永远不能 self-approve PR, 但 admin 又必须有 PR 流程
#       (PR #20 之前手动 GitHub UI 关 enforce_admins → merge → 恢复, 3 次都这么做, 易错)
#
# 解决: 一键脚本 — 备份 BP → 关 enforce_admins → merge → 恢复 BP → 记录
#       失败/中断时自动 trap 恢复 BP (避免裸奔)
#
# 用法:
#   ./scripts/admin-merge.sh <PR_NUMBER>             # squash merge (default)
#   ./scripts/admin-merge.sh <PR_NUMBER> --rebase    # rebase merge
#   ./scripts/admin-merge.sh --dry-run <PR_NUMBER>   # 备份 BP 不 merge
#
# 必须: ~/.git-credentials 里有 token (用 setup-credentials.sh setup)

set -euo pipefail

# Initialize globals (set -u friendly)
GH_HTTP_CODE=""
GH_HTTP_CODE_FILE="/tmp/admin-merge-gh-code.$$"
: > "$GH_HTTP_CODE_FILE"
trap 'rm -f "$GH_HTTP_CODE_FILE"' EXIT

REPO="398qq/aierp"
BRANCH="master"
LOG_DIR="${LOG_DIR:-$HOME/aierp/logs}"
LOG_FILE="$LOG_DIR/admin-merge.log"
BP_BACKUP_DIR="$LOG_DIR/bp-backups"
CRED_FILE="$HOME/.git-credentials"

mkdir -p "$LOG_DIR" "$BP_BACKUP_DIR"

# Colors
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m'

log()  { echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $*" | tee -a "$LOG_FILE"; }
err()  { echo -e "${RED}[ERR]${NC} $*" | tee -a "$LOG_FILE" >&2; }
ok()   { echo -e "${GREEN}[OK]${NC} $*" | tee -a "$LOG_FILE"; }

# ============ Get token from credential helper ============
get_token() {
    if [[ -f "$CRED_FILE" ]] && [[ -s "$CRED_FILE" ]]; then
        # URL may be https://x-access-token:REAL_PAT@github.com (set by 'git -c url.https://...push')
        # or https://REAL_PAT@github.com. Take the password part (after last ':') for auth header.
        grep -oP 'https://(?:x-access-token:)?\K[^@]+' "$CRED_FILE" | tail -1 | sed 's/^.*://'
        return 0
    fi
    return 1
}

# ============ GitHub API helper ============
gh_api() {
    # gh_api METHOD PATH [DATA]  →  echoes response, returns http_code via global
    local method="$1"
    local path="$2"
    local data="${3:-}"
    local retries="${4:-3}"
    local token
    token="$(get_token)" || { err "No token in $CRED_FILE. Run scripts/setup-credentials.sh first."; exit 1; }

    local attempt=0
    while [[ $attempt -lt $retries ]]; do
        attempt=$((attempt + 1))
        local args=(-sS --connect-timeout 10 --max-time 60 -X "$method"
                    -H "Authorization: token $token"
                    -H "Accept: application/vnd.github+json"
                    -H "X-GitHub-Api-Version: 2022-11-28"
                    -w "\n%{http_code}" "https://api.github.com$path")
        if [[ -n "$data" ]]; then
            args=(-H "Content-Type: application/json" -d "$data" "${args[@]}")
        fi

        local response
        response=$(curl "${args[@]}" 2>/dev/null)
        local code
        code=$(echo "$response" | tail -1)
        if [[ "$code" =~ ^[2-3][0-9][0-9]$ ]]; then
            echo "$code" > "$GH_HTTP_CODE_FILE"
            echo "$response" | sed '$d'
            return 0
        fi
        if [[ $attempt -lt $retries ]]; then
            warn "API $method $path returned $code (attempt $attempt/$retries), retrying in 3s..."
            sleep 3
        else
            echo "$code" > "$GH_HTTP_CODE_FILE"
            echo ""
        fi
    done
    return 1
}

# ============ Parse args ============
DRY_RUN=false
MERGE_METHOD="squash"
PR_NUMBER=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run) DRY_RUN=true; shift ;;
        --squash)  MERGE_METHOD="squash"; shift ;;
        --rebase)  MERGE_METHOD="rebase"; shift ;;
        --merge)   MERGE_METHOD="merge"; shift ;;
        -h|--help)
            grep -E "^# " "$0" | sed 's/^# *//' | head -20
            exit 0
            ;;
        *)
            if [[ -z "$PR_NUMBER" ]] && [[ "$1" =~ ^[0-9]+$ ]]; then
                PR_NUMBER="$1"
                shift
            else
                err "Unknown arg: $1"
                exit 1
            fi
            ;;
    esac
done

if [[ -z "$PR_NUMBER" ]]; then
    err "Usage: $0 <PR_NUMBER> [--squash|--rebase|--merge] [--dry-run]"
    exit 1
fi

# ============ Pre-flight ============
log "=========================================="
log "admin-merge: PR #$PR_NUMBER (method: $MERGE_METHOD, dry-run: $DRY_RUN)"

# Token check
TOKEN=$(get_token) || { err "No token in $CRED_FILE. Run scripts/setup-credentials.sh first."; exit 1; }

# Get PR info
PR_JSON=$(gh_api GET "/repos/$REPO/pulls/$PR_NUMBER")
PR_STATE=$(echo "$PR_JSON" | jq -r '.state // "UNKNOWN"')
PR_TITLE=$(echo "$PR_JSON" | jq -r '.title // "UNKNOWN"')
PR_MERGEABLE=$(echo "$PR_JSON" | jq -r '.mergeable // null')
PR_HEAD_SHA=$(echo "$PR_JSON" | jq -r '.head.sha // "UNKNOWN"')

log "PR state: $PR_STATE, title: $PR_TITLE"
log "PR mergeable: $PR_MERGEABLE, head SHA: ${PR_HEAD_SHA:0:8}"

if [[ "$PR_STATE" != "open" ]]; then
    err "PR is not open (state: $PR_STATE). Aborting."
    exit 1
fi

# ============ Step 1: Backup BP ============
BP_BACKUP_FILE="$BP_BACKUP_DIR/master-$(date +%Y%m%d_%H%M%S)-pr${PR_NUMBER}.json"
log "Backing up current BP to $BP_BACKUP_FILE..."

BP_BEFORE=$(gh_api GET "/repos/$REPO/branches/$BRANCH/protection")
if [[ "$(cat "$GH_HTTP_CODE_FILE" 2>/dev/null || echo "")" != "200" ]]; then
    err "Failed to fetch current BP (HTTP $(cat "$GH_HTTP_CODE_FILE" 2>/dev/null || echo "")). Aborting."
    exit 1
fi

echo "$BP_BEFORE" > "$BP_BACKUP_FILE"
BP_SUMMARY=$(echo "$BP_BEFORE" | jq -c '{
    enforce_admins: .enforce_admins.enabled,
    required_approvals: .required_pull_request_reviews.required_approving_review_count,
    require_code_owner_reviews: .required_pull_request_reviews.require_code_owner_reviews,
    strict: .required_status_checks.strict,
    contexts_count: (.required_status_checks.contexts | length)
}' 2>/dev/null)
log "BP before: $BP_SUMMARY"

# CRITICAL: Sanity check that backup is in known-good state.
# If current BP is somehow misconfigured (e.g. enforce_admins=false from a failed previous run),
# we should NOT backup that as the restore baseline, otherwise we'll "restore" to a broken state.
ENFORCE_BEFORE=$(echo "$BP_BEFORE" | jq -r '.enforce_admins.enabled')
if [[ "$ENFORCE_BEFORE" != "true" ]]; then
    warn "Current BP has enforce_admins=$ENFORCE_BEFORE (unexpected, expected true)."
    warn "This usually means a previous admin-merge run failed to restore BP."
    warn "Will not proceed until BP is verified correct. Run:"
    warn "  gh api -X PUT -H 'Content-Type: application/json' -d @/tmp/bp-fix.json \\"
    warn "    /repos/$REPO/branches/$BRANCH/protection"
    err "Aborting for safety. Fix BP first, then re-run."
    exit 1
fi
ok "BP backed up (known-good baseline: enforce_admins=true)"

# ============ Step 2: Disable enforce_admins ============
restore_bp() {
    log "Restoring BP from $BP_BACKUP_FILE..."
    # PUT body schema (different from GET response):
    #   - enforce_admins: bool (not {enabled: bool})
    #   - restrictions: null for personal repos
    local restore_body
    restore_body=$(jq '{
        required_status_checks: {strict: .required_status_checks.strict, contexts: .required_status_checks.contexts},
        required_pull_request_reviews: {
            dismiss_stale_reviews: .required_pull_request_reviews.dismiss_stale_reviews,
            require_code_owner_reviews: .required_pull_request_reviews.require_code_owner_reviews,
            require_last_push_approval: .required_pull_request_reviews.require_last_push_approval,
            required_approving_review_count: .required_pull_request_reviews.required_approving_review_count
        },
        restrictions: null,
        enforce_admins: .enforce_admins.enabled
    }' "$BP_BACKUP_FILE")
    local response
    response=$(gh_api PUT "/repos/$REPO/branches/$BRANCH/protection" "$restore_body")
    if [[ "$(cat "$GH_HTTP_CODE_FILE" 2>/dev/null || echo "")" == "200" ]]; then
        ok "BP restored"
        return 0
    else
        err "FAILED to restore BP (HTTP $(cat "$GH_HTTP_CODE_FILE" 2>/dev/null || echo "")). Manual restore required."
        err "File: $BP_BACKUP_FILE"
        return 1
    fi
}

if [[ "$DRY_RUN" == "true" ]]; then
    log "[DRY-RUN] Would: DELETE enforce_admins → merge PR #$PR_NUMBER (--$MERGE_METHOD) → restore BP"
    log "[DRY-RUN] Backup saved: $BP_BACKUP_FILE"
    log "[DRY-RUN] No changes made."
    exit 0
fi

# Trap for safety: if anything fails after this point, restore BP
trap 'restore_bp || err "BP restore FAILED - manual intervention needed"' ERR INT TERM

log "Disabling enforce_admins (admin override)..."
ENFORCE_RESP=$(gh_api DELETE "/repos/$REPO/branches/$BRANCH/protection/enforce_admins")
ENFORCE_AFTER=$(echo "$ENFORCE_RESP" | jq -r '.enabled | tostring' 2>/dev/null || echo "unknown")
log "enforce_admins after toggle: $ENFORCE_AFTER"

if [[ "$ENFORCE_AFTER" != "false" ]]; then
    # Fallback: PUT full BP with enforce_admins=false
    log "DELETE endpoint didn't return false, trying PUT full BP approach..."
    # GitHub PUT body schema (not the same as GET response):
    #   - enforce_admins: bool (not {enabled: bool})
    #   - restrictions: null for personal repos (no users/teams allowed)
    #   - required_pull_request_reviews: object
    #   - required_status_checks: object
    MODIFIED_BP=$(jq '{
        required_status_checks: {strict: .required_status_checks.strict, contexts: .required_status_checks.contexts},
        required_pull_request_reviews: {
            dismiss_stale_reviews: .required_pull_request_reviews.dismiss_stale_reviews,
            require_code_owner_reviews: .required_pull_request_reviews.require_code_owner_reviews,
            require_last_push_approval: .required_pull_request_reviews.require_last_push_approval,
            required_approving_review_count: .required_pull_request_reviews.required_approving_review_count
        },
        restrictions: null,
        enforce_admins: false
    }' "$BP_BACKUP_FILE")
    gh_api PUT "/repos/$REPO/branches/$BRANCH/protection" "$MODIFIED_BP" >/dev/null
    if [[ "$(cat "$GH_HTTP_CODE_FILE" 2>/dev/null || echo "")" != "200" ]]; then
        err "Failed to disable enforce_admins (HTTP $(cat "$GH_HTTP_CODE_FILE" 2>/dev/null || echo "")). Aborting."
        exit 1
    fi
    # Re-fetch to confirm
    ENFORCE_RESP=$(gh_api GET "/repos/$REPO/branches/$BRANCH/protection/enforce_admins")
    ENFORCE_AFTER=$(echo "$ENFORCE_RESP" | jq -r '.enabled | tostring' 2>/dev/null || echo "unknown")
    log "enforce_admins after PUT fallback: $ENFORCE_AFTER"
fi

if [[ "$ENFORCE_AFTER" != "false" ]]; then
    err "enforce_admins still $ENFORCE_AFTER after toggle. Aborting."
    exit 1
fi
ok "enforce_admins disabled (admin override active)"

# ============ Step 3: Merge PR ============
log "Merging PR #$PR_NUMBER with --$MERGE_METHOD..."

MERGE_BODY=$(jq -n --arg m "$MERGE_METHOD" '{merge_method: $m}')
MERGE_RESP=$(gh_api PUT "/repos/$REPO/pulls/$PR_NUMBER/merge" "$MERGE_BODY")

MERGE_SHA=$(echo "$MERGE_RESP" | jq -r '.sha // ""' 2>/dev/null)
MERGE_MSG=$(echo "$MERGE_RESP" | jq -r '.message // empty' 2>/dev/null)

if [[ -z "$MERGE_SHA" ]] || [[ "$(cat "$GH_HTTP_CODE_FILE" 2>/dev/null || echo "")" != "200" ]]; then
    err "Merge failed (HTTP $(cat "$GH_HTTP_CODE_FILE" 2>/dev/null || echo ""), msg: $MERGE_MSG). Restoring BP."
    exit 1
fi
ok "PR merged (commit: ${MERGE_SHA:0:8})"

# Clear trap — past the risky point
trap - ERR INT TERM

# ============ Step 4: Restore BP ============
restore_bp

# Verify restore
ENFORCE_FINAL_RESP=$(gh_api GET "/repos/$REPO/branches/$BRANCH/protection/enforce_admins")
ENFORCE_FINAL=$(echo "$ENFORCE_FINAL_RESP" | jq -r '.enabled | tostring' 2>/dev/null || echo "unknown")
log "enforce_admins final: $ENFORCE_FINAL"

if [[ "$ENFORCE_FINAL" != "true" ]]; then
    err "BP restore incomplete — enforce_admins should be true but is $ENFORCE_FINAL"
    err "Manual restore: curl -X PUT -H 'Authorization: token ***' \\"
    err "       -d @$BP_BACKUP_FILE https://api.github.com/repos/$REPO/branches/$BRANCH/protection"
    exit 1
fi
ok "BP fully restored (enforce_admins back to true)"

# ============ Step 5: Delete merged branch ============
HEAD_REF=$(echo "$PR_JSON" | jq -r '.head.ref // empty')
if [[ -n "$HEAD_REF" ]]; then
    log "Deleting remote branch: $HEAD_REF"
    DEL_RESP=$(gh_api DELETE "/repos/$REPO/git/refs/heads/$HEAD_REF")
    if [[ "$(cat "$GH_HTTP_CODE_FILE" 2>/dev/null || echo "")" == "204" ]]; then
        ok "Remote branch deleted"
    else
        warn "Failed to delete remote branch (HTTP $(cat "$GH_HTTP_CODE_FILE" 2>/dev/null || echo "")). Manual cleanup if needed."
    fi
fi

# ============ Step 6: Summary ============
log "=========================================="
log "✅ admin-merge complete"
log "PR:        #$PR_NUMBER — $PR_TITLE"
log "Method:    $MERGE_METHOD"
log "Merge SHA: $MERGE_SHA"
log "BP file:   $BP_BACKUP_FILE"
log "Log:       $LOG_FILE"
log "=========================================="
