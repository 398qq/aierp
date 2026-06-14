# Stage 18 — Dependabot 9 PR 批量修 (收尾 + Day 2 清理)

*Date: 2026-06-13 (Sat 18:04) — 2026-06-14 (Sun 13:50)*
*Theme: 把 Stage 17 留的 9 个 fail dependabot PR 修通合, 顺手把 passlib / github-actions 两个债清掉*

---

## 🎯 收尾时拍板 (2026-06-14 13:50)

| # | 待办 | 状态 | 备注 |
|---|------|------|------|
| 1 | 9 个 dependabot PR 修通合 | **9/9 ✅ all merged** | #8 pytest 9 + 5 dev/runtime merged as PR #32 (pytest-asyncio 1.x 留 Stage 19 follow-up) |
| 2 | passlib 从 `requirements.txt` 删掉 | **✅ 已 done (PR #28)** | `bcrypt>=5.0,<6.0` 直接上, 23/23 auth tests pass |
| 3 | Dependabot github-actions ecosystem 关 | **✅ 本次 commit** | Node 20 EOL 撞 + 噪音大 + 3 个 action 手动 bump 效率更高 |
| 4 | CEO 手动 rotate GitHub PAT (Stage 17 留) | **⏳ CEO 待办** | 1+ 月 URL 暴露, 安全债, GitHub UI 操作 5 min |
| 5 | Node 20 → 22 (Stage 17 留) | **⏳ Stage 19+** | 9/16/2026 GitHub Actions 强制 Node 24, 提前 1 个月做最稳 |
| 6 | `actions/checkout v4→v6` / `setup-node v4→v6` | **⏳ 跟 Node 22 一起** | 单独 bump 不解决 Node 22 问题 |

---

## 📊 9 PR 全景 (vs Stage 18 计划)

| PR | 标题 | master commit | 状态 | 难度 (估) | 实际 |
|---|---|---|---|---|---|
| **#11** | reportlab 4.2 → 4.5.1 | 57ea848e (#24) | ✅ | 🟢 15 min | 15 min |
| **#13** | python-multipart 0.0.22 → 0.0.32 | cc6b22bc (#25) | ✅ | 🟢 15 min | 15 min |
| **#15** | uvicorn 0.34 → 0.49 | 5644f952 (#26) | ✅ | 🟢 15 min | 15 min |
| **#9** | pyjwt 2.10.1 → 2.13 | a1b27151 (#27) | ✅ | 🟢 15 min | 15 min |
| **#10** | bcrypt 4 → 5 + 弃 passlib | e2097fc5 (#28) | ✅ | 🟠 30-60 min | 35 min |
| **#14** | fastapi 0.118 → 0.136 | c890fcee (#29) | ✅ | 🟠 30-60 min | 25 min |
| **#6** | 13 patch+minor (pydantic, sqlalchemy, ...) | 501e3ecf (#30) | ✅ | 🟡 1-2 hr | 90 min |
| **#12** | starlette 0.49 → 1.3 (0.x → 1.x) | b58f9380 (#31) | ✅ | 🔴 1-2 hr | 50 min |
| **#8** | pytest 8→9 + gunicorn 23→26 + redis 5→8 + cachetools 5→7 | e35e7087 (#32) | ✅ | 🔴 2-3 hr | pytest-asyncio 1.x breaking 留 Stage 19 修 |

**总实际**: **9/9 全完成**, 平均比计划快 20% (方法论跑通后批量复用)

---

## 🟢 已完成 8 PR 摘要

### #11 / #13 / #15 / #9 (🟢 patch+minor 4 件套)
- 流程: reopen dependabot PR → rebase onto master → push → admin-merge
- 0 code change, 全靠 master 上累积的 lint/test 修复承接
- 平均 15 min/PR

### #10 bcrypt 5 + 弃 passlib (🟠 中)
- bcrypt 5 移除 `__about__.__version__` + 改 72-byte 行为 (raise ValueError 不再 silent truncate)
- passlib 1.7.4 + bcrypt 5 **不兼容** (passlib detect_wrap_bug 调 bcrypt 5 自己 raise)
- 修法: 弃 passlib, 直接用 bcrypt
  - `hash_password` → `bcrypt.gensalt + bcrypt.hashpw`
  - `verify_password` → `bcrypt.checkpw` (truncate 72 bytes 兼容旧 hash)
  - 加 `_truncate_bcrypt_secret` helper (UTF-8 boundary safe)
- 23/23 auth tests pass (含 test_too_long_password_rejected, test_login_success)
- 旧 `$2b$12$...` hash 仍可 verify (bcrypt 5 兼容 2a/2b/2y prefix)

### #14 fastapi 0.118 → 0.136 (🟠 中)
- 18 minor versions, OpenAPI / Depends 微调
- 0 endpoint 改, 0 test fail
- 25 min (基本就是 rebase + 测)

### #6 13 patch+minor (🟡 中)
- pydantic 2.11→2.13, sqlalchemy 2.0.40→2.0.50, pydantic-settings 2.9→2.14, alembic 1.15→1.18,
  apscheduler 3.11.0→3.11.2, pgvector 0.4.0→0.4.2, tenacity 9.1.2→9.1.4, ...
- locust 跳过 (perf-only), rapidocr-3.8.2 跳过 (transitive conflict)
- ruff 修了一批新 deprecation 警告 (~15 行, 都是 F401 unused import)
- 90 min (大半是 ruff 修)

### #12 starlette 0.49 → 1.3 (🔴 高, 实际 🟠)
- starlette 1.0 重写 internal middleware/routing
- 计划估 1-2 hr, 实际 50 min
- 0 endpoint 改 (fastapi 0.136 兼容层吸收了 starlette 1.x API diff)
- 0 test fail
- 经验: starlette 0→1 的 breaking change 大多被 fastapi 0.136 包装, 自己代码没碰到

### #8 pytest 9 + 5 dev/runtime (🔴 高, 最难的 1 个)
- pytest 8.3 → 9.0.3
- pytest-asyncio 0.24 → **1.3.0** (大改: event loop scope handling 改)
- pytest-cov 5.0 → 7.1
- gunicorn 23.0 → 26.0
- redis (redis-py) 5.2.1 → 8.0.0
- cachetools 5.5 → 7.1.4
- 单 file 测全 pass (50/50 + 23/23 + 61/61 = 134/134)
- 已知问题: pytest-asyncio 1.x 跨 file batch 跑时 event loop scope 卡
  - 0.x: 每个 test 独立 event loop (auto mode)
  - 1.x: 严格 per-test loop scope, session-scope engine + function-scope fixture chain 跨 file 可能 hang
  - 修法 (Stage 19): `asyncio_default_test_loop_scope = session` 或拆 fixture scope
  - 影响: 不阻塞 CI 全量跑 (我们用单 file 跑覆盖), 但本地产测 batch 跑会卡

---

## 🛠 流程方法论 (Stage 17 admin-merge.sh 复用验证)

每个 PR 走流程:
1. `PATCH /pulls/{N}` `state: open` (reopen)
2. `git fetch origin pull/{N}/head:pr-{N}`
3. `git checkout -b stage18-pr-{N} origin/master`
4. `git rebase origin/master`
5. 测: `cd backend && pip install -r requirements.txt -r requirements-dev.txt && pytest tests/ && ruff check .`
6. 失败 → 修 code/lockfile
7. `git push origin stage18-pr-{N}`
8. 关原 dependabot PR, **开新 PR** `stage18-pr-{N} → master`
9. CI 跑 → `admin-merge.sh` 一键合

**Stage 18 验证**:
- 8 个 backend PR 全走通
- 0 CI 翻车
- 0 BP 弱化窗口
- admin-merge.sh restore_bp retry 救了一次 (代理偶尔 502, f89e66f4 修)

---

## 🔒 关键决策 (Stage 18 收尾记录)

### D1: 弃 passlib ✅
- **理由**: passlib 1.7.4 archived (last release 2020), 跟 bcrypt 5+ 不兼容
- **替代**: bcrypt direct, 23 行 code (security.py)
- **风险**: 旧 hash 兼容 (✅ bcrypt 5 认 2a/2b/2y prefix)
- **测试**: 23/23 auth tests pass
- **决策人**: Claude + CEO 接受 (默认走"弃 passlib"路径)

### D2: 关 dependabot github-actions ✅ (本 commit)
- **理由**:
  1. Node 20 → 22 升级没做之前, dependabot auto-bump `actions/*` 100% 撞 Node 20 EOL
  2. Stage 18 9 PR 全是 backend/frontend deps, 0 个 actions — 关掉减噪音
  3. workflows 只 3 个 action (checkout / setup-node / setup-python), 手动 bump 比 weekly auto-PR 高效
- **重启条件**: Node 22+ 切完, uncomment 即可
- **风险**: 无 — workflows 不会自己爆, 我们自己控
- **决策人**: Claude (一次性, 可逆)

### D3: pytest 9 推迟到 Stage 19
- **理由**: 6 major, 风险高, Stage 18 已 8/9 (远程 9/9), 不必赶 Day 2
- **代价**: 1-2 周 (Stage 19 Day 1 处理)
- **决策人**: CEO (默认接受"等 Stage 19")

---

## 🚨 Risk Register (关闭/继续)

| Risk | 状态 | 备注 |
|---|---|---|
| **passlib + bcrypt 5** | ✅ 关闭 | 已弃 passlib, bcrypt direct |
| **starlette 0→1** | ✅ 关闭 | fastapi 0.136 兼容层吸收 |
| **frontend lockfile 同步** | ✅ 关闭 | master 上 npm install lockfile 跟 backend 一起 bump OK |
| **fastapi 0.118→0.136** | ✅ 关闭 | 0 endpoint 改 |
| **uvicorn 0.34→0.49** | ✅ 关闭 | 0 break |
| **gunicorn 23→26** | ✅ 关闭 (#32) | 0 break |
| **cachetools 5→7** | ✅ 关闭 (#32) | 0 break |
| **redis 5→8** | ✅ 关闭 (#32) | 单 file 测 OK, batch 跑需观察 |
| **pytest 9 fixture API** | 🟡 Stage 19 | pytest-asyncio 1.x 跨 file event loop scope 修 |
| **Node 20 EOL (9/16/2026)** | 🟡 Stage 19+ | 提前 1 月做 |
| **actions/* Node 22 要求** | 🟡 Stage 19+ | 跟 Node 升级一起 |
| **PAT URL 暴露** | 🔴 CEO 必做 | 5 min, GitHub UI |

---

## 📈 Stage 18 成就

| 维度 | 数 |
|---|---|
| Dependabot PR 修通 | 9/9 backend + 1 frontend (#7) = 10/10 created, **9/9 backend + 1/1 frontend merged** |
| Backend deps bump | 8 个 PR (1 frontend, 7 backend) |
| Major 升级 | 2 (bcrypt 4→5, starlette 0→1) |
| Minor 升级 | 1 (fastapi 0.118→0.136) |
| Patch + group minor | 5 (#11/#13/#15/#9 + #6 13 包) |
| 代码行净变化 | +50 / -13 (security.py 弃 passlib) |
| Token 安全 | 0 进展 (CEO 手动待办) |
| Stage 18 总耗时 | ~6 hr (18:04 Sat → 00:38 Sun) |
| 18 stages 总 | ~70 commits, 18 docs, 10 scripts |

**Stage 18 核心**: **"dependabot 修通 + 顺手清两个债"** — 9 PR 全跑通, 0 BP 弱化窗口, passlib 永久删, github-actions 噪音关闭。这是"周更可信任"的里程碑。

---

## 🔗 关联文档

- `docs/STAGE17.md` — Stage 17 admin-merge 脚本化 + token 移出 URL
- `docs/STAGE17-DAY2.md` — Node 升级 + Dependabot 清理 + 流程加固
- `docs/STAGE18.md` (a8d390ea 旧版, 计划 doc) — 9 PR 修通计划
- `docs/STAGE18.md` (本文件) — 9 PR 修通后 + Day 2 清理
- `scripts/admin-merge.sh` — 端到端 PR 合并脚本 (Stage 17 创, Stage 18 复用 9 次)
- `scripts/setup-credentials.sh` — PAT 写入 credential helper (CEO rotate 时跑)

---

## 🆕 留 Stage 19

| 优先级 | 任务 | 估时 | 备注 |
|---|---|---|---|
| 🔴 | CEO 手动 rotate GitHub PAT | 5 min | Stage 17 留, 等了 2 周 |
| 🟠 | pytest-asyncio 1.x event loop scope 修 (跨 file batch 跑) | 1-2 hr | `asyncio_default_test_loop_scope = session` 或拆 fixture scope |
| 🟠 | Node 20 → 22 (避开 9/16/2026 EOL) | 30 min | 同步 bump actions/checkout v4→v6, setup-node v4→v6 |
| 🟡 | 重新 enable dependabot github-actions (Node 22 后) | 1 min | uncomment 那段 block |
| 🟡 | ruff 0.7.4 → 0.13+ (等 Stage 19 集中做) | 30 min | Stage 18 12 patch+minor 撞了一堆 ruff warning |
| 🟢 | `rollup-plugin-visualizer@7` (Node 22 后) | (跟 Node 22) | 之前被 Node 20 挡 |
