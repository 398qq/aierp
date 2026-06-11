#!/usr/bin/env bash
# Stage 13 Day 2: Frontend bundle size check
# 跑 build, 统计每个 chunk 大小, 超过阈值则 fail
# 适合 CI / pre-merge 跑

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$FRONTEND_DIR"

# 阈值 (KB, 未压缩)
WARN_CHUNK_KB=800   # 单 chunk 警告阈值
ERROR_CHUNK_KB=1500 # 单 chunk 错误阈值
WARN_TOTAL_KB=4000  # 总体警告阈值
ERROR_TOTAL_KB=6000 # 总体错误阈值

echo "🔨 Building frontend..."
npm run build 2>&1 | tail -5

echo ""
echo "📊 Bundle size report:"
DIST_DIR="$FRONTEND_DIR/dist/assets"
if [ ! -d "$DIST_DIR" ]; then
  echo "❌ dist/assets not found — build failed?"
  exit 1
fi

TOTAL_KB=0
FAIL=0

# 按大小排序
for f in $(ls -S "$DIST_DIR"/*.js 2>/dev/null); do
  SIZE_KB=$(($(stat -c%s "$f") / 1024))
  TOTAL_KB=$((TOTAL_KB + SIZE_KB))
  HUMAN=$(numfmt --to=iec --suffix=B "$((SIZE_KB * 1024))" 2>/dev/null || echo "${SIZE_KB}KB")
  STATUS="✅"
  if [ "$SIZE_KB" -ge "$ERROR_CHUNK_KB" ]; then
    STATUS="❌ OVER BUDGET"
    FAIL=1
  elif [ "$SIZE_KB" -ge "$WARN_CHUNK_KB" ]; then
    STATUS="⚠️  WARNING"
  fi
  printf "  %-10s %-50s %s\n" "$HUMAN" "$(basename "$f")" "$STATUS"
done

echo ""
HUMAN_TOTAL=$(numfmt --to=iec --suffix=B "$((TOTAL_KB * 1024))" 2>/dev/null || echo "${TOTAL_KB}KB")
echo "📦 Total JS: $HUMAN_TOTAL (${TOTAL_KB}KB)"
if [ "$TOTAL_KB" -ge "$ERROR_TOTAL_KB" ]; then
  echo "❌ TOTAL OVER BUDGET (>${ERROR_TOTAL_KB}KB)"
  FAIL=1
elif [ "$TOTAL_KB" -ge "$WARN_TOTAL_KB" ]; then
  echo "⚠️  TOTAL WARNING (>${WARN_TOTAL_KB}KB)"
fi

if [ -f "$FRONTEND_DIR/dist/stats.html" ]; then
  echo ""
  echo "📈 Treemap visualization: $FRONTEND_DIR/dist/stats.html"
fi

if [ "$FAIL" -eq 1 ]; then
  echo ""
  echo "❌ Bundle size check FAILED"
  exit 1
fi

echo ""
echo "✅ Bundle size check PASSED"
