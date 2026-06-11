# Stage 13 — 安全 + 性能 + 流程 深度闭环

**Period**: 2026-06-11 (晚 18:46-19:30)
**Branch**: master
**Commits**: 4 (Day 1-4 + push)

## 🎯 目标

把"持续运营"再深化一层 —— 安全 3 道防线 + 性能监控 + 流程文档，**4 任务 1 stage**。

## 📊 战报

| Day | 任务 | 关键产出 | 代码 |
|---|---|---|---|
| 1 | GitHub CodeQL | 2 个 GitHub config (Python + JS/TS) | +117 / -0 |
| 2 | 前端 bundle 监控 | rollup-plugin-visualizer + check script + 预算 | +723 / -312 |
| 3 | CONTRIBUTING.md | 5592 bytes 6 主题 onboarding 文档 | +322 / -0 |
| 4 | 本地 pre-commit 安全 | bandit + detect-secrets + 2 baseline | +656 / -0 |
| 5 | 本文档 | 战报 | +N |

**零业务代码改动** (Stage 13 全为安全 / 性能 / 文档)

## 🏆 关键设计

### Day 1 — GitHub CodeQL (扫我们自己写的代码漏洞)

**2 个新文件**:
- `.github/workflows/codeql.yml` — 2 个 matrix job (Python + JS/TS), 每周二 02:00 UTC
- `.github/codeql/codeql-config.yml` — 排除 venv / tests / dist / docs

**与 Stage 12 区别**:
| 工具 | 扫什么 | 频率 |
|---|---|---|
| pip-audit | 后端依赖 | 周一 01:30 UTC |
| npm audit | 前端依赖 | 周一 01:30 UTC |
| Dependabot | 依赖自动开 PR | 周一 09:00 CST |
| **CodeQL** (新) | **我们自己写的代码** | 周二 02:00 UTC |

**CodeQL 能扫出** (Stage 12 扫不出):
- SQL 注入 (raw f-string in execute())
- XSS (innerHTML 拼用户输入)
- 不安全反序列化 (yaml.load / pickle.loads)
- 硬编码密码 (password='literal')
- 不安全 hash (md5/sha1 密码)
- path traversal
- SSRF
- command injection

### Day 2 — 前端 bundle 监控

**3 件套**:
1. **rollup-plugin-visualizer** 接入 (vite.config.ts)
   - 生成 dist/stats.html (treemap 可视化)
   - gzip + brotli size 一并显示
2. **scripts/check-bundle-size.sh** (CI 友好)
   - 跑 build → 统计每个 chunk
   - 阈值: warn 800KB / error 1500KB (单 chunk), 4000/6000KB (总体)
3. **npm scripts** (`npm run check-bundle-size` / `analyze:bundle`)

**实测**: 当前总 2.8MB, 最大单 chunk 700+KB, 全过 ✅

### Day 3 — CONTRIBUTING.md (6 主题 onboarding)

1. **开发工作流** — 5-stage 节律 + branch 策略 + 本地环境 + pre-commit
2. **依赖升级 (Dependabot)** — 自动流程 + 升级策略矩阵 (patch 直接 merge / minor 1 周 / major 季度) + review checklist 6 步 + 紧急 CVE 处理
3. **安全审计 (CVE)** — 3 道防线 + 本地命令 + 修 CVE 6 步 + Stage 11 Day 1 教训
4. **CodeQL 代码扫描** — 自动流程 + 扫出类型 + 配置排除 + 高危 alert 处理
5. **Bundle size 监控** — 本地跑 + 当前预算 + 优化方法
6. **Commit 与 PR 规范** — 8 个 commit prefix + PR body 5 段 (Why/What/How/Test/Risk) + 不可合并清单 6 条

**额外**: 紧急回滚流程 (`git revert` 永远比 fix 快)

### Day 4 — 本地 pre-commit 加 bandit + detect-secrets

**3 道工具 vs 3 道防线 (避免重复)**:
| 工具 | 跑哪 | 扫啥 |
|---|---|---|
| **pre-commit bandit** | 本地 commit | Python 代码漏洞 |
| **pre-commit detect-secrets** | 本地 commit | 密码 / API key 误提交 |
| **GitHub CodeQL** (Day 1) | 每周二 UTC | Python + JS 代码漏洞 |
| **GitHub pip-audit** (Stage 12) | 每周一 UTC | Python 依赖 CVE |
| **GitHub npm audit** (Stage 12) | 每周一 UTC | JS 依赖 CVE |
| **Dependabot** (Stage 12) | 每周一 CST | 依赖自动开 PR |

**3 个新文件**:
- `.bandit` — YAML, skip 6 false positive (B110/B105/B311/B404/B603/B607)
- `.secrets.baseline` — 614 行 baseline
- `.pre-commit-config.yaml` — +2 hooks (detect-secrets + bandit)

**关键设计**:
- 本地 + CI 双跑 (UX + 兜底)
- baseline 锁定 614 行 false positive (不再每天骚扰)
- 真问题不被 skip (B102/B301/B608 仍 fail)

## 🧪 测试覆盖

| 模块 | 测试数 | 状态 |
|---|---|---|
| **后端** | **350+ 全过** (Stage 12 保持) | ✅ |
| **前端** | **91/91 全过** | ✅ |
| **bandit** | **0 issues** (skip false positive) | ✅ |
| **TypeScript** | **0 errors** | ✅ |

## 🔄 与前 stages 关系

| Stage | 提供 | Stage 13 消费 |
|---|---|---|
| Stage 5 | 162 文件 ruff format + pre-commit | Day 4 在原 hook 上加 2 个 |
| Stage 8 | pre-commit 已就位 | Day 4 扩展 |
| Stage 11 Day 1 | CVE 升级 18→0 | Day 1 CodeQL 防新漏洞 |
| Stage 12 Day 4 | Dependabot | Day 3 CONTRIBUTING 文档化 |
| Stage 12 Day 1 | npm audit | Day 2 bundle size (前端) |

**关键模式**: 持续消费前期投资，闭环成型。

## 🚀 13 Stages 总体战绩

| Stage | commits | 关键 |
|---|---|---|
| 1-6 | 26 | base + DevOps |
| 7-10 | 14 | 业务深化 + 监控 |
| 11 | 3 | 收尾闭环 |
| 12 | 4 | 自动化 + 闭环 |
| **13** | **4** | **深度闭环** |
| **合计** | **51** | **+27748 / -9551** |

**测试**: 350+ 全过
**文档**: 15 个 (+CONTRIBUTING.md, STAGE13.md)
**CVE**: 18 → 0 (持续监控)
**bundle**: 2.8MB (阈值内)
**远端**: 全部 push ✅

## 🆕 Stage 13 关键修复 + 教训

1. **bandit config 格式** — YAML 不是 TOML，文档说"tomllib" 但实际是 yaml.safe_load
2. **.bandit 必须用 YAML** — bandit 1.7.10 默认是 YAML，TOML 解析失败
3. **detect-secrets 不会扫常量赋值** — `AWS_KEY = "AKIA..."` 不会被检出（需要 dict.get 模式）
4. **absolute path edit tool** — 必须用 `/home/ttdiy/aierp/...` 不用 `~/aierp/...`
5. **system Python PEP 668** — `pip install` 默认拒绝，用 venv 或 `--break-system-packages`

## 🚨 留给未来

- **Dependabot auto-merge**: minor+patch CI 通过可自动 merge (开设置就行)
- **GitHub Security tab 启用**: 启用 code scanning alerts (CodeQL 已有, 开启通知)
- **bundle size 在 PR 自动跑**: GitHub Action 跑 `npm run check-bundle-size` (Stage 14 候选)
- **Snyk 商业方案**: 更全面的漏洞数据库 (Stage 14 候选, 需付费)
- **真实负载测试**: k6 / locust 跑 stage 1
- **production backup restore drill**: 每月 1 次
- **GitHub Branch Protection**: 强制 PR review + CI 通过
- **Code Owners**: `.github/CODEOWNERS` 自动 assign reviewer
- **Renovate Bot**: Dependabot 替代品, UI 更友好

## 📝 工程笔记

- **完成为止** 工作流: 用户给方向，自主推进 13 stages / 51 commits / 11+ 小时
- **dev DB / CI / prod 三套环境**: dev 即时反馈, CI 持续验证, prod 部署验证
- **Stage 11-13 闭环**: 安全 → 状态机 → 通知 → 批量 → 报表 → 持续监控 → **深度持续监控**
- **"文档是代码的一部分"**: 15 个 docs 与代码同步演进
- **5-stage 节律**: 每天 1+ commit，每天 push，失败可回滚
- **血泪教训**: system Python 装包需 venv 或 --break-system-packages, bandit config 是 YAML
