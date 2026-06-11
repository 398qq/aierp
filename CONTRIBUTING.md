# Contributing to AIERP

> **贡献者必读**。Stage 13 Day 3 沉淀的 PR review 流程，特别是 **Dependabot 自动 PR 怎么 merge**。

## 📋 目录

1. [开发工作流](#开发工作流)
2. [依赖升级 (Dependabot)](#依赖升级-dependabot)
3. [安全审计 (CVE 检查)](#安全审计-cve-检查)
4. [CodeQL 代码扫描](#codeql-代码扫描)
5. [Bundle size 监控](#bundle-size-监控)
6. [Commit 与 PR 规范](#commit-与-pr-规范)
7. [测试要求](#测试要求)

---

## 开发工作流

### 5-stage 节律

每天 1+ commit、每天 push、失败可回滚。Stage 1-13 沉淀的工作流。

### Branch 策略

- `master` 永远可发布
- Feature 在 feature branch，PR 合并到 master
- 不长期存活 dev branch

### 本地环境

```bash
# Backend
cd backend && source venv/bin/activate
alembic upgrade head  # 跑最新迁移
python -m pytest -x   # 关键测试

# Frontend
cd frontend && npm install
npm test              # 跑全部测试
npm run check-bundle-size  # bundle 大小检查
```

### Pre-commit hooks (本地)

Stage 8 Day 4 加的 `.pre-commit-config.yaml`：
- ruff format
- ruff lint
- prettier format
- eslint (前端)

commit 前自动跑，**CI 不通过本地也别想推**。

---

## 依赖升级 (Dependabot)

### 自动流程

Stage 12 Day 4 加的 `.github/dependabot.yml`，每周一 **09:00 Asia/Shanghai** 自动开 PR。

3 个生态：
- `deps(backend)` — pip
- `deps(frontend)` — npm
- `ci(actions)` — GitHub Actions

PR 自动带 3 个 label：
- `dependencies`
- 生态名 (backend / frontend / ci)
- `security` (如果是 CVE 修复)

### 升级策略矩阵

| 类型 | 例子 | 策略 | 等待时间 |
|---|---|---|---|
| **patch** | 1.0.X → 1.0.Y | 直接 merge | 0 天 |
| **minor** | 1.X.0 → 1.Y.0 | 跑测试 + 看 changelog | 1 周 |
| **major** | X.0.0 → Y.0.0 | 规划升级窗口 | 季度 |

### Dependabot PR review checklist

收到 Dependabot PR 后：

- [ ] 1. 看 PR title — `deps(backend): bump fastapi from 0.115.12 to 0.116.0`
- [ ] 2. 看 changed files — `requirements.txt` / `package.json` / `package-lock.json`
- [ ] 3. CI 跑没 — 3 个 workflow 全绿？
  - backend-lint, backend-test, frontend-test
  - security-audit (Stage 12 Day 4)
- [ ] 4. 本地跑关键测试
- [ ] 5. minor/major: 看 GitHub release notes
- [ ] 6. 没问题就 merge squash

### 紧急 CVE 处理

Critical CVE (远程代码执行 / 凭据泄露)：
1. 跳过 Dependabot 等周一
2. 手动 `pip install -U` / `npm update`
3. 跑 security-audit workflow dispatch
4. 测试通过立即 merge
5. 通知团队 (`memory/YYYY-MM-DD.md` 写一条)

---

## 安全审计 (CVE 检查)

### 3 道防线

| 工具 | 范围 | 频率 | 触发 | 文件 |
|---|---|---|---|---|
| **pip-audit** | Python 依赖 | 每周一 01:30 UTC | schedule + push/PR | `.github/workflows/security-audit.yml` |
| **npm audit** | JS 依赖 | 每周一 01:30 UTC | schedule + push/PR | 同上 |
| **Dependabot** | 依赖自动开 PR | 每周一 09:00 CST | schedule | `.github/dependabot.yml` |

### 本地跑

```bash
# Backend
cd backend && pip-audit -r requirements.txt --strict

# Frontend
cd frontend && npm audit
```

### 修 CVE 的步骤

1. 跑 `pip-audit --strict` 找到漏洞
2. 查 PyPI 是否有安全版
3. 升包: `pip install -U <package>`
4. 跑 `pytest` + `npm test` 验证零回归
5. 改 `requirements.txt` / `package.json` + lock
6. commit + PR (label `security`)

### Stage 11 Day 1 教训

- 优先用 **PyJWT** 替代 **python-jose** (jose 3 年不维护)
- 改 1 行 import 就修 2 个 transitive 漏洞
- 不盲升大版本, 看 changelog

---

## CodeQL 代码扫描

### 自动流程

`.github/workflows/codeql.yml`，**每周二 02:00 UTC** 跑 + push/PR 触发。

扫 2 个语言：
- Python (backend/)
- JavaScript/TypeScript (frontend/)

扫出类型 (Stage 12 工具扫不出)：
- SQL 注入
- XSS
- 不安全反序列化 (yaml.load / pickle.loads)
- 硬编码密码
- 不安全 hash (md5 / sha1)
- path traversal
- SSRF
- command injection

### 看结果

GitHub → Security tab → Code scanning alerts

### 配置排除

`.github/codeql/codeql-config.yml` 排除：
- 缓存 (`__pycache__`, `venv`, `node_modules`)
- Alembic 模板
- tests/ (测试代码)
- 构建产物 (`dist/`, `coverage/`)
- 文档 (`*.md`)

**改排除前**：确认该路径真的不在生产代码路径上。

### 高危 alert 处理

1. 看 alert 详情 (具体文件 + 行号 + 漏洞类型)
2. 修代码 / 加白名单 (`# codeql[js/sql-injection]`)
3. 跑测试验证
4. 标 false positive 还是 true positive
5. commit + close alert

---

## Bundle size 监控

### 自动 (未来)

Stage 14 候选：GitHub Action 在 PR 跑 `npm run check-bundle-size`。

### 本地跑

```bash
cd frontend && npm run check-bundle-size
```

输出：
- 单 chunk 大小 (按 size 排序)
- 总体大小
- 阈值超 → exit 1

### 当前预算 (未压缩)

| 类别 | 警告 | 错误 |
|---|---|---|
| 单 chunk | 800 KB | 1500 KB |
| 总体 | 4000 KB | 6000 KB |

### 优化方法

1. 看 `dist/stats.html` (treemap)
2. 找最大 chunk — 一般是 antd / recharts / 业务大组件
3. 优化方向：
   - 按需 import (`import { Button } from 'antd'`)
   - 路由 lazy load (`React.lazy`)
   - 替代轻量库 (dayjs 替 moment)

---

## Commit 与 PR 规范

### Commit prefix

```
feat:        新功能
fix:         修 bug
docs:        文档
refactor:    重构
ci:          CI/CD
deps:        依赖
test:        测试
chore:       杂事
```

### 例子

```
feat(commission): 批量审批 endpoint
fix(jwt): 替换 python-jose → PyJWT
docs(stage13): STAGE13.md 战报
ci(codeql): GitHub CodeQL workflow
deps(backend): bump fastapi 0.115.12 → 0.116.0
```

### PR 规范

- Title 简洁: 动词 + 对象
- Body 5 段:
  1. **Why** — 解决什么问题
  2. **What** — 主要改动
  3. **How** — 关键设计
  4. **Test** — 测试覆盖
  5. **Risk** — 风险评估

### 不可合并的 PR

- ❌ CI 红
- ❌ security-audit fail
- ❌ 关键测试 fail
- ❌ bundle size 超过 budget
- ❌ 缺测试覆盖 (新功能)
- ❌ commit message 不规范

---

## 测试要求

### 覆盖率

| 模块 | 最低 |
|---|---|
| service | 80% |
| api | 70% |
| utils | 90% |
| frontend component | 60% |

### 跑测试

```bash
# Backend
cd backend && pytest -x                # 关键测试
cd backend && pytest                    # 全部
cd backend && pytest --cov=app         # 覆盖率

# Frontend
cd frontend && npm test                # vitest
cd frontend && npm run test:coverage   # 覆盖率
```

### 测试命名

- `test_<unit>_<scenario>.py`
- `it <should> <when>` (BDD 风格)

---

## 紧急回滚

PR merge 后发现问题：

```bash
# 找到问题 commit
git log --oneline | head -5

# Revert (创建新 commit, 不动历史)
git revert <bad-commit-hash>
git push origin master
```

**revert 永远比 fix 快** — 先恢复服务，再追根因。

---

## 联系

- **CEO**: 刘经理 (Telegram: 8103002093)
- **Agent**: A-Zhu (OpenClaw)
- **远端**: https://github.com/398qq/aierp

---

*Stage 13 Day 3 沉淀。下次新人 onboard 直接看这份。*
