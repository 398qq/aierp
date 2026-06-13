#!/bin/bash
# setup-credentials.sh — 一键配置 aierp 仓库的 GitHub 凭证
#
# Stage 17 Day 1 引入。之前 .git/config 的 remote URL 硬编码了 PAT，
# 任何 git clone / git log 都会泄露到屏幕/日志/备份里。
# 现在改成: URL 干净 + token 存 ~/.git-credentials (chmod 600)
#
# 用法:
#   ./scripts/setup-credentials.sh                       # 用 ~/.git-credentials 现有 token
#   ./scripts/setup-credentials.sh <NEW_TOKEN>           # 用新 token (e.g. CEO 刚 rotate 的)
#   ./scripts/setup-credentials.sh --rotate              # 提示 CEO 在 GitHub 手动 rotate

set -euo pipefail

REPO_REMOTE="https://github.com/398qq/aierp.git"
CRED_FILE="$HOME/.git-credentials"

# Colors
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m'

log()  { echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
err()  { echo -e "${RED}[ERR]${NC} $*" >&2; }
ok()   { echo -e "${GREEN}[OK]${NC} $*"; }

# ============ Step 0: Pre-flight ============
log "Pre-flight checks..."

# Ensure we're in a git repo with the aierp remote
if ! git rev-parse --git-dir >/dev/null 2>&1; then
    err "Not in a git repo. cd to aierp first."
    exit 1
fi

CURRENT_URL=$(git config --get remote.origin.url 2>/dev/null || echo "")
if [[ "$CURRENT_URL" != *"$REPO_REMOTE"* ]] && [[ "$CURRENT_URL" != *"$REPO_REMOTE".git* ]]; then
    err "Remote URL is not aierp: $CURRENT_URL"
    err "Expected: $REPO_REMOTE"
    exit 1
fi

# Check if URL still has token in it (the bug we're fixing)
if echo "$CURRENT_URL" | grep -q "@github.com"; then
    warn "URL still has token embedded: $CURRENT_URL"
    warn "This script will clean it up. Confirming in 3s..."
    sleep 3
fi

# ============ Step 1: Get or use existing token ============
if [[ "${1:-}" == "--rotate" ]]; then
    cat <<'EOF'
┌──────────────────────────────────────────────────────────────────┐
│  🔐 Manual token rotation required                               │
│                                                                  │
│  1. 打开 https://github.com/settings/pats                        │
│  2. 找到当前 aierp 用的 PAT (admin 权限)                         │
│  3. 选 "Delete" (revoke) — 立刻吊销                             │
│  4. 选 "Generate new token" (Fine-grained)                       │
│  5. 资源: 仅勾选 398qq/aierp                                     │
│  6. 权限 (最小集):                                               │
│     - Contents: Read and write                                   │
│     - Pull requests: Read and write                              │
│     - Workflows: Read and write                                  │
│     - Metadata: Read-only (auto)                                │
│  7. 选 "Generate token" → 复制                                   │
│  8. 回到这里跑: ./scripts/setup-credentials.sh <NEW_TOKEN>        │
│  9. (可选) 把新 token 同步到 GitHub Secret `AUTO_MERGE_TOKEN`    │
│     gh secret set AUTO_MERGE_TOKEN --body "<NEW_TOKEN>" --repo 398qq/aierp │
└──────────────────────────────────────────────────────────────────┘
EOF
    exit 0
fi

if [[ -n "${1:-}" ]]; then
    TOKEN="$1"
    log "Using provided token (first 10 chars): ${TOKEN:0:10}..."
else
    # Try to read existing token from helper
    if [[ -f "$CRED_FILE" ]] && [[ -s "$CRED_FILE" ]]; then
        # URL may be https://x-access-token:REAL_PAT@github.com (set by 'git -c url.https://...push')
        # or https://REAL_PAT@github.com. Take the password part (after last ':') for auth header.
        TOKEN=$(grep -oP 'https://(?:x-access-token:)?\K[^@]+' "$CRED_FILE" | tail -1 | sed 's/^.*://')
        if [[ -n "$TOKEN" ]]; then
            log "Reusing existing token from $CRED_FILE"
        fi
    fi

    if [[ -z "${TOKEN:-}" ]]; then
        err "No token found. Usage:"
        err "  $0 <TOKEN>          # set new token"
        err "  $0 --rotate         # show rotation guide"
        exit 1
    fi
fi

# ============ Step 2: Validate token ============
log "Validating token via GitHub API..."
HTTP_CODE=$(curl -sS -o /tmp/gh-user.json -w "%{http_code}" \
    -H "Authorization: token $TOKEN" \
    "https://api.github.com/user" 2>/dev/null || echo "000")

if [[ "$HTTP_CODE" != "200" ]]; then
    err "Token validation failed (HTTP $HTTP_CODE). Check token is correct."
    [[ -s /tmp/gh-user.json ]] && cat /tmp/gh-user.json | head -5
    exit 1
fi

LOGIN=$(python3 -c "import json; d=json.load(open('/tmp/gh-user.json')); print(d.get('login', '?'))")
log "Token valid for user: $LOGIN"

# ============ Step 3: Write credential helper ============
log "Writing token to $CRED_FILE (chmod 600)..."
echo "https://${TOKEN}@github.com" > "$CRED_FILE"
chmod 600 "$CRED_FILE"
ok "Token stored in credential helper"

# ============ Step 4: Clean remote URL ============
log "Cleaning remote URL (removing embedded token)..."
git remote set-url origin "$REPO_REMOTE"
NEW_URL=$(git config --get remote.origin.url)
log "New remote URL: $NEW_URL"

# Verify no token in URL
if echo "$NEW_URL" | grep -q "@github.com"; then
    err "URL still has @github.com! Cleanup failed."
    exit 1
fi
ok "URL is clean"

# ============ Step 5: Test auth ============
log "Testing git auth via credential helper..."
if git ls-remote origin HEAD >/dev/null 2>&1; then
    ok "git ls-remote origin HEAD works (credential helper functional)"
else
    err "git auth test failed. Try: git credential fill (interactive)"
    exit 1
fi

# ============ Summary ============
cat <<EOF

┌──────────────────────────────────────────────────────────────────┐
│  ✅ Setup complete                                                │
│                                                                  │
│  Remote URL: $NEW_URL
│  Token file: $CRED_FILE (chmod 600)
│  User:       $LOGIN
│                                                                  │
│  🔒 安全提示:                                                    │
│  - 不要再把 token 粘回 URL 或 commit 到任何文件                  │
│  - 备份时排除 ~/.git-credentials                                  │
│  - CEO 提示: 用 $0 --rotate 查看手动 rotate 步骤                 │
└──────────────────────────────────────────────────────────────────┘
EOF
