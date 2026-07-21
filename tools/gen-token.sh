#!/bin/bash
# 生成 AIERP API Token 并同步到所有需要的地方
# 用法: bash tools/gen-token.sh

set -e
cd "$(dirname "$0")/../backend"

echo "正在生成 AIERP Token (365天有效)..."

TOKEN=$(python3 -c "
from app.core.security import create_access_token
from app.config import settings
original = settings.JWT_EXPIRE_MINUTES
settings.JWT_EXPIRE_MINUTES = 365 * 24 * 60
token = create_access_token(user_id=1, username='admin', token_version=1)
settings.JWT_EXPIRE_MINUTES = original
print(token)
" | tail -1)

echo "Token: ${TOKEN:0:30}..."

# 验证 (重试 3 次，每次间隔 3 秒，后端可能还未启动)
for i in 1 2 3; do
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
    http://localhost:8080/api/v1/auth/me \
    -H "Authorization: Bearer $TOKEN" 2>/dev/null || echo "000")
  if [ "$STATUS" = "200" ]; then
    echo "✅ Token 验证通过"
    break
  fi
  if [ "$i" = "3" ]; then
    echo "⚠️  Token 验证未通过 (HTTP $STATUS) — 后端可能未启动，token 已写入配置，下次后端启动后生效"
  else
    sleep 3
  fi
done

# 1. 写入 shell profile (所有终端+子进程可用)
grep -q "AIERP_TOKEN" "$HOME/.bashrc" 2>/dev/null && \
  sed -i '/export AIERP_TOKEN=/d' "$HOME/.bashrc" && \
  sed -i '/export AIERP_BASE_URL=/d' "$HOME/.bashrc"

cat >> "$HOME/.bashrc" << BASHEOF
export AIERP_BASE_URL="http://localhost:8080/api/v1"
export AIERP_TOKEN="$TOKEN"
BASHEOF
echo "✅ ~/.bashrc 已更新"

# 2. 导入到 systemd 用户服务环境 (OpenClaw 子进程可用)
systemctl --user import-environment AIERP_BASE_URL AIERP_TOKEN 2>/dev/null || true
echo "✅ systemd 环境已更新"

# 3. 更新 OpenClaw 配置文件
python3 -c "
import json
with open('$HOME/.openclaw/openclaw.json') as f:
    cfg = json.load(f)
cfg.setdefault('env', {})['AIERP_BASE_URL'] = 'http://localhost:8080/api/v1'
cfg.setdefault('env', {})['AIERP_TOKEN'] = '$TOKEN'
with open('$HOME/.openclaw/openclaw.json', 'w') as f:
    json.dump(cfg, f, indent=2, ensure_ascii=False)
print('✅ OpenClaw.json 已更新')
"

echo ""
echo "重启 OpenClaw (如已运行)..."
openclaw gateway restart 2>&1 | tail -1 || echo "⚠️  OpenClaw 未运行，跳过重启"

# 4. 更新 Hermes 配置
grep -q "AIERP_TOKEN" "$HOME/.hermes/.env" 2>/dev/null && \
  sed -i '/export AIERP_TOKEN=/d' "$HOME/.hermes/.env" && \
  sed -i '/export AIERP_BASE_URL=/d' "$HOME/.hermes/.env" && \
  sed -i '/^# AIERP/d' "$HOME/.hermes/.env" && \
  sed -i '/^AIERP_BASE_URL=/d' "$HOME/.hermes/.env" && \
  sed -i '/^AIERP_TOKEN=/d' "$HOME/.hermes/.env"

cat >> "$HOME/.hermes/.env" << HERMESEOF

# AIERP
AIERP_BASE_URL="http://localhost:8080/api/v1"
AIERP_TOKEN="$TOKEN"
HERMESEOF
echo "✅ ~/.hermes/.env 已更新"

# 5. 重启 Hermes Gateway 使配置生效
hermes gateway restart 2>&1 | tail -1 || echo "⚠️  Hermes 未运行，跳过重启"

echo ""
echo "完成! Token 已同步到:"
echo "   ~/.bashrc          → 所有终端"
echo "   systemd user env   → OpenClaw 子进程"
echo "   openclaw.json      → 网关配置"
echo "   ~/.hermes/.env     → Hermes Agent"
