"""Regression test: SQL injection pattern audit (Stage 19 P2 #2).

Scans backend/app/ for dangerous SQL patterns that would bypass SQLAlchemy
ORM parameter binding.  Fails the test suite if any are introduced — CI
guard against future regressions.

Allowlist contains documented exceptions; bump with security review only.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

BACKEND_APP = Path(__file__).parent.parent / "app"

# Patterns that indicate string interpolation INTO a SQL execution path.
# ORM-bound parameters (col.ilike(f"%{x}%"), select(...).where(col == x)) are SAFE
# because SQLAlchemy binds the whole value as a parameter — these are NOT flagged.
DANGEROUS_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # text() — SQLAlchemy raw SQL; must never use f-string or concat
    (re.compile(r'\btext\s*\(\s*f["\']'), "text() with f-string"),
    (re.compile(r'\btext\s*\([^)]*\+'), "text() with concatenation"),
    # execute() — raw SQL execution path
    (
        re.compile(r'\b(?:db|session|conn)\.execute\s*\(\s*f["\']'),
        "execute() with f-string",
    ),
    (
        re.compile(r'\b(?:db|session|conn)\.execute\s*\(\s*["\'][^"\']*["\']\s*\+'),
        "execute() with string concat",
    ),
    # Query-builder methods — these accept SQL expressions, not raw SQL,
    # so f-string here is a red flag (use bound params instead)
    (
        re.compile(r'\b(?:select|update|delete|insert)\s*\(\s*f["\']'),
        "query builder with f-string",
    ),
    # psycopg2 / DBAPI cursor.execute raw SQL
    (re.compile(r'\bcursor\.execute\s*\(\s*f["\']'), "cursor.execute() with f-string"),
    (
        re.compile(r'\bcursor\.execute\s*\(\s*["\'][^"\']*["\']\s*\+'),
        "cursor.execute() with string concat",
    ),
    # .format() or %-formatting directly in execute()
    (
        re.compile(r'\.execute\s*\([^)]*\.format\s*\('),
        "execute() with .format()",
    ),
    (
        re.compile(r'\.execute\s*\(\s*["\'][^"\']*%[sd]'),
        "execute() with %s/%d substitution",
    ),
]

# Documented safe exceptions.  Each entry is (relative_path, line_number_range_or_none).
# Adding a new entry requires a security team review (CODEOWNERS).
ALLOWLIST: dict[str, str] = {
    # cache_delete uses f-string for cache key, NOT SQL — backend/app/services/cache_service.py
    "backend/app/services/cache_service.py": "cache key construction (Redis), not SQL",
}


def _is_comment_line(line: str) -> bool:
    stripped = line.lstrip()
    return stripped.startswith("#")


def _is_import_line(line: str) -> bool:
    stripped = line.lstrip()
    return stripped.startswith("from ") or stripped.startswith("import ")


def _scan_file(path: Path) -> list[tuple[str, int, str, str]]:
    """Return list of (rel_path, line_no, pattern_desc, line_text)."""
    findings: list[tuple[str, int, str, str]] = []
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return findings

    rel = path.relative_to(path.parent.parent).as_posix()
    allowlisted_file = rel in ALLOWLIST

    for lineno, line in enumerate(text.splitlines(), 1):
        if _is_comment_line(line) or _is_import_line(line):
            continue
        if allowlisted_file:
            continue
        for pattern, desc in DANGEROUS_PATTERNS:
            if pattern.search(line):
                findings.append((rel, lineno, desc, line.strip()[:120]))
    return findings


def test_no_sql_injection_patterns() -> None:
    """No dangerous SQL patterns should exist in backend/app/."""
    findings: list[tuple[str, int, str, str]] = []
    for py_file in BACKEND_APP.rglob("*.py"):
        if "__pycache__" in py_file.parts:
            continue
        findings.extend(_scan_file(py_file))

    if findings:
        lines = "\n".join(
            f"  {rel}:{ln}: [{desc}] {snippet}" for rel, ln, desc, snippet in findings
        )
        pytest.fail(
            f"SQL injection audit found {len(findings)} dangerous pattern(s):\n"
            f"{lines}\n\n"
            f"Fix: use SQLAlchemy ORM with bound parameters. "
            f"Document any false positive by adding to ALLOWLIST in this test."
        )


def test_allowlist_size_stable() -> None:
    """Allowlist should not grow without security review.

    Bump this assertion + the security test review checklist when adding entries.
    """
    assert len(ALLOWLIST) <= 1, (
        f"Allowlist grew to {len(ALLOWLIST)} entries. "
        "Requires security team review before merging."
    )


def test_audit_report_exists() -> None:
    """Stage 19 P2 #2 audit report must exist at docs/security/."""
    repo_root = Path(__file__).parent.parent.parent
    report = repo_root / "docs" / "security" / "stage19-p2-sql-injection-audit.md"
    assert report.exists(), f"Missing audit report: {report}"
    content = report.read_text(encoding="utf-8")
    assert "0 个 SQL 注入漏洞" in content or "0 SQL injection" in content, (
        "Audit report missing summary conclusion"
    )
