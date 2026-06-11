# CI 流程（Stage 4, 2026-06-11）

## 目标

让 CI 从"摆设"变"真管用"——lint/format/test/build 任何一步失败，**PR 阻塞**。

## 5 个 Job

`.github/workflows/ci.yml` 触发条件：push / PR 到 master / main

| Job | 工具 | 触发条件 | 失败行为 |
|---|---|---|---|
| `backend-lint` | ruff 0.7.4 | 每次 push | ❌ 阻塞 |
| `backend-test` | pytest | 每次 push | ❌ 阻塞 |
| `frontend-typecheck` | tsc --noEmit | 每次 push | ❌ 阻塞 |
| `frontend-test` | vitest | 每次 push | ❌ 阻塞 |
| `frontend-build` | vite build | 每次 push | ❌ 阻塞 |

**改进前**：1 个 backend + 1 个 frontend job，所有步骤 `|| true` 吞错误——CI 形同虚设。
**改进后**：5 个独立 job，pip/npm cache 加速，同分支 push 自动取消上一次。

## Pre-commit Hook

`.pre-commit-config.yaml` 提供 7 个本地 hook：

```bash
# 首次安装（团队成员必做）
pre-commit install

# 全文件跑一次
pre-commit run --all-files
```

| Hook | 作用 |
|---|---|
| ruff --fix | Python lint 错误自动修（exit non-zero on fix）|
| trailing-whitespace | 去行尾空格 |
| end-of-file-fixer | 补 EOF 换行 |
| check-yaml | YAML 语法 |
| check-json | JSON 语法 |
| check-merge-conflict | 找 merge 冲突标记 |
| detect-private-key | 找泄漏的私钥 |

**暂不启用 ruff-format**：会 reformat 246 个文件，diff 太乱。等团队按模块逐步启用。

## Ruff 配置（隐含默认）

`backend/` 用了 ruff 默认规则。统计：
- E / W：pycodestyle（行长度、空格）
- F：pyflakes（unused import / var）
- I：isort（import 排序）
- B：bugbear（常见 bug 模式）
- UP：pyupgrade（Python 语法升级）
- N：pep8-naming

如果需要自定义，加 `backend/pyproject.toml`：

```toml
[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "W", "F", "I", "B", "UP", "N", "SIM", "C4", "PT"]
ignore = ["E501"]  # line too long（ruff format 会管）
```

## 常见问题

### Q: CI 在我本地通过，但远端失败？

答：CI 用 `pip install -r requirements.txt`（**不是** `pip install -r requirements-dev.txt` 之外的额外包）。本地装个 `-r requirements-dev.txt` 之外的包会假阴性。

### Q: ruff check 失败但本地没改 Python？

答：可能 `__pycache__` 还在。`find . -name '__pycache__' -exec rm -rf {} + 2>/dev/null`

### Q: pre-commit hook 卡住？

答：第一次跑会下载镜像（`ruff-pre-commit`、`pre-commit-hooks`），网络可能慢。`git commit --no-verify` 可绕过（**不推荐**）。

### Q: ruff format 想启用？

答：分步走：
```bash
# 1. 一次性格式化所有文件
ruff format backend/

# 2. CI 加上 format check
#    .github/workflows/ci.yml 加：
#    - run: ruff format --check app/ tests/

# 3. pre-commit 启用 format hook
#    .pre-commit-config.yaml 删掉 "Note: ruff-format is intentionally not enabled"
```

## Stage 4 战绩

| 指标 | 之前 | 之后 |
|---|---|---|
| CI job 数 | 3 | 5（拆细）|
| `\|\| true` 吞错 | 4 处 | 0 处 |
| cache 复用 | 0 | pip + npm |
| concurrency cancel | ❌ | ✅ |
| pre-commit | ❌ | ✅（7 hook）|
| ruff 错误 | 22 | 0 |
| 净代码 | 0 | -37 行（删 unused import）|

## Stage 5 准备

- **迁移规范**：DB migration 走 alembic 单一入口（不用 SQL 文件）
- **CSS 拆分**：CustomerList.css 12K → 散到各组件
- **products/index.tsx 拆分**：1573 行 → 类似 stage3 customers 模式
- **ESLint**：frontend 缺 lint（CI 跑 typecheck 但没 style 检查）
- **deps 审计**：`pip-audit` + `npm audit`
- **Codecov**：coverage 上传 + badge
- **PR template**：写明改了什么、影响范围、测试
