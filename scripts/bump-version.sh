#!/usr/bin/env bash
# bump-version.sh — bump AIERP version across all files, commit, tag, and push.
#
# Usage:
#   ./scripts/bump-version.sh patch          # 2.0.0 → 2.0.1
#   ./scripts/bump-version.sh minor          # 2.0.0 → 2.1.0
#   ./scripts/bump-version.sh major          # 2.0.0 → 3.0.0
#   ./scripts/bump-version.sh 2.1.0          # set exact version
#
# Files updated:
#   - backend/app/config.py   (VERSION: str)
#   - frontend/package.json   ("version")
#
# Steps: bump → verify → commit → tag → push

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BUMP="${1:-patch}"

# ── helpers ─────────────────────────────────────────────────────────────

current_version() {
  grep -oE '"?VERSION"?[[:space:]]*[:=][[:space:]]*"[^"]+"' \
    "$ROOT/backend/app/config.py" \
    | head -1 \
    | grep -oE '[0-9]+\.[0-9]+\.[0-9]+'
}

bump_semver() {
  local from="$1" part="$2"
  local major minor patch
  IFS='.' read -r major minor patch <<< "$from"
  case "$part" in
    major) echo "$((major + 1)).0.0" ;;
    minor) echo "${major}.$((minor + 1)).0" ;;
    patch) echo "${major}.${minor}.$((patch + 1))" ;;
    *)     echo "$part" ;;  # literal version string
  esac
}

# ── determine versions ──────────────────────────────────────────────────

OLD="$(current_version)"

if [[ "$BUMP" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  NEW="$BUMP"
else
  NEW="$(bump_semver "$OLD" "$BUMP")"
fi

if [ "$OLD" = "$NEW" ]; then
  echo "ERROR: new version ($NEW) equals old version ($OLD). Nothing to do." >&2
  exit 1
fi

echo "Bumping: $OLD → $NEW"
echo ""

# ── update files ────────────────────────────────────────────────────────

# backend/app/config.py
sed -i "s/VERSION[[:space:]]*:[[:space:]]*str[[:space:]]*=[[:space:]]*\"$OLD\"/VERSION: str = \"$NEW\"/" \
  "$ROOT/backend/app/config.py"

# frontend/package.json
sed -i "s/\"version\": \"$OLD\"/\"version\": \"$NEW\"/" \
  "$ROOT/frontend/package.json"

# ── verify ──────────────────────────────────────────────────────────────

echo "Verifying updates..."
MISSING=$(grep -rn "\"$OLD\"" "$ROOT/backend/app/config.py" "$ROOT/frontend/package.json" 2>/dev/null || true)
FOUND=$(grep -rn "\"$NEW\"" "$ROOT/backend/app/config.py" "$ROOT/frontend/package.json" 2>/dev/null || true)

if [ -n "$MISSING" ]; then
  echo "WARNING: old version still present:"
  echo "$MISSING"
fi

echo "New version references:"
echo "$FOUND"
echo ""

# ── commit + tag + push ────────────────────────────────────────────────

echo "Committing and tagging..."
cd "$ROOT"

git add backend/app/config.py frontend/package.json
git commit -m "chore: bump version to $NEW"
git tag -a "v$NEW" -m "Version $NEW"

echo ""
echo "Pushing to origin..."
git push origin HEAD
git push origin "v$NEW"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✓ Version bumped: $OLD → $NEW"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Next steps (optional):"
echo "  gh release create v$NEW --title \"v$NEW\" --generate-notes"
echo ""
