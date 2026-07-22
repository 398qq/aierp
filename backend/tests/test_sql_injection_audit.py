"""SQL 注入审计 — 回归测试（Stage 19 P2 #2）

扫描 backend/app/ 下的所有 .py 文件，检测可能引入 SQL 注入的反模式：
- f-string 进 execute()/text()
- 字符串拼接进 execute()/text()
- .format() 进 execute()
- %s/%d 进 execute()
- select/update/delete/insert() 接收 f-string（应该用 ORM 参数化）

如果发现违规，测试失败并列出文件 + 行号 + 违规类型。
Allowlist: cache_delete 用 f-string 拼缓存 key（不是 SQL），加白名单。

跑法: pytest backend/tests/test_sql_injection_audit.py -v
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

BACKEND_APP = Path(__file__).parent.parent / "app"

# 危险模式：name -> (regex, 描述, allowlist 文件)
DANGEROUS_PATTERNS: list[tuple[re.Pattern[str], str, frozenset[str]]] = [
    # f-string 进 execute()/text() — 高危
    (re.compile(r"\bexecute\s*\(\s*f['\"]"), "execute() with f-string", frozenset()),
    (re.compile(r"\btext\s*\(\s*f['\"]"), "text() with f-string", frozenset()),
    # 字符串拼接进 execute()/text() — 高危
    (
        re.compile(r'\bexecute\s*\(\s*["\'].*["\']?\s*\+'),
        "execute() with string concat",
        frozenset(),
    ),
    (
        re.compile(r'\btext\s*\(\s*["\'].*["\']?\s*\+'),
        "text() with string concat",
        frozenset(),
    ),
    # .format() 进 execute() — 中危
    (
        re.compile(r"\bexecute\s*\([^)]*\.format\s*\("),
        "execute() with .format()",
        frozenset(),
    ),
    # %s/%d 进 execute() — 中危
    (
        re.compile(r"\bexecute\s*\(\s*['\"][^'\"]*%[sd]"),
        "execute() with %s/%d",
        frozenset(),
    ),
    # select/update/delete/insert() 接收 f-string — 应该走 ORM 参数化
    (
        re.compile(r"\bselect\s*\(\s*f['\"]"),
        "select() with f-string",
        frozenset(),
    ),
    (
        re.compile(r"\binsert\s*\(\s*f['\"]"),
        "insert() with f-string",
        frozenset(),
    ),
    (
        re.compile(r"\bupdate\s*\(\s*f['\"]"),
        "update() with f-string",
        frozenset(),
    ),
    (
        re.compile(r"\bdelete\s*\(\s*f['\"]"),
        "delete() with f-string",
        frozenset(),
    ),
]

# 完全跳过扫描的文件（不是源码）
SKIP_PATHS = frozenset(
    {
        "__pycache__",
        "tests",
        "migrations",
    }
)

# 已知安全的 allowlist：cache_service.py 用 f-string 拼 Redis key（非 SQL）
PATH_ALLOWLIST: dict[str, str] = {
    "backend/app/services/cache_service.py": "cache key 拼 Redis key，非 SQL",
}


def _is_comment_or_import(line: str) -> bool:
    stripped = line.strip()
    return (
        stripped.startswith("#")
        or stripped.startswith("//")
        or stripped.startswith("from ")
        or stripped.startswith("import ")
    )


def _scan_file(py_file: Path) -> list[tuple[int, str, str]]:
    """扫描单个文件，返回违规列表 [(line_no, pattern_desc, line_text)]"""
    violations = []
    try:
        text = py_file.read_text(encoding="utf-8")
    except (UnicodeDecodeError, FileNotFoundError):
        return violations

    rel_path = str(py_file)
    if any(skip in rel_path for skip in SKIP_PATHS):
        return violations

    for lineno, line in enumerate(text.splitlines(), 1):
        if _is_comment_or_import(line):
            continue
        for pattern, desc, allowlist in DANGEROUS_PATTERNS:
            if pattern.search(line):
                # 检查 allowlist
                allowed = False
                for allowed_path, reason in PATH_ALLOWLIST.items():
                    if allowed_path in rel_path:
                        # 该文件整文件 allowlist
                        allowed = True
                        break
                if allowed:
                    continue
                violations.append((lineno, desc, line.strip()[:100]))
    return violations


@pytest.fixture(scope="module")
def all_violations() -> list[tuple[str, int, str, str]]:
    """扫描所有文件，汇总违规"""
    all_v = []
    for py_file in BACKEND_APP.rglob("*.py"):
        if any(skip in str(py_file) for skip in SKIP_PATHS):
            continue
        for lineno, desc, line in _scan_file(py_file):
            rel = str(py_file.relative_to(py_file.parent.parent))
            all_v.append((rel, lineno, desc, line))
    return all_v


def test_no_fstring_in_execute(all_violations):
    """不允许 f-string 进入 execute()"""
    fstring_violations = [v for v in all_violations if "f-string" in v[2]]
    if fstring_violations:
        msg = "\n".join(f"  {v[0]}:{v[1]}: [{v[2]}] {v[3]}" for v in fstring_violations)
        pytest.fail(f"Found {len(fstring_violations)} f-string in execute/text:\n{msg}")


def test_no_string_concat_in_execute(all_violations):
    """不允许字符串拼接进入 execute()"""
    concat_violations = [v for v in all_violations if "concat" in v[2]]
    if concat_violations:
        msg = "\n".join(f"  {v[0]}:{v[1]}: [{v[2]}] {v[3]}" for v in concat_violations)
        pytest.fail(f"Found {len(concat_violations)} concat in execute/text:\n{msg}")


def test_no_format_in_execute(all_violations):
    """不允许 .format() 进入 execute()"""
    fmt_violations = [v for v in all_violations if ".format" in v[2]]
    if fmt_violations:
        msg = "\n".join(f"  {v[0]}:{v[1]}: [{v[2]}] {v[3]}" for v in fmt_violations)
        pytest.fail(f"Found {len(fmt_violations)} .format() in execute:\n{msg}")


def test_no_percent_in_execute(all_violations):
    """不允许 %s/%d 进入 execute()"""
    pct_violations = [v for v in all_violations if "%s/%d" in v[2]]
    if pct_violations:
        msg = "\n".join(f"  {v[0]}:{v[1]}: [{v[2]}] {v[3]}" for v in pct_violations)
        pytest.fail(f"Found {len(pct_violations)} %s/%d in execute:\n{msg}")


def test_no_fstring_in_query_builder(all_violations):
    """不允许 f-string 进入 select/insert/update/delete()"""
    qb_violations = [
        v
        for v in all_violations
        if any(op in v[2] for op in ["select()", "insert()", "update()", "delete()"])
    ]
    if qb_violations:
        msg = "\n".join(f"  {v[0]}:{v[1]}: [{v[2]}] {v[3]}" for v in qb_violations)
        pytest.fail(f"Found {len(qb_violations)} f-string in query builder:\n{msg}")


def test_audit_report_exists():
    """审计报告必须存在"""
    report = Path(__file__).parent.parent.parent / "docs" / "security" / "stage19-p2-sql-injection-audit.md"
    assert report.exists(), f"Missing audit report: {report}"


def test_bandit_available():
    """bandit 工具必须可用"""
    import shutil

    assert shutil.which("bandit") is not None, "bandit not installed"


def test_allowlist_documented():
    """allowlist 必须有文档说明"""
    for path, reason in PATH_ALLOWLIST.items():
        assert reason, f"Allowlist entry {path} missing reason"
