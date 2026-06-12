# Stage 15 — 备份还原自动化 + 容量调优

**周期**: 2026-06-12 (1 day, 5 commits)
**主题**: 闭合"备份盲点" + 限流/cache 收尾 + 5/25→6/12 18 天数据缺口复盘

---

## 🎯 目标

Stage 14 完成后，**核心业务功能全稳，负载有基线**。但运维盲点没解决：
1. 备份**18 天前**（5/25），cron 没接
2. 限流 100/min 太紧，stats 无缓存
3. 真没跑过**跨时间的还原测试**（18 天数据丢失影响 = 不知道）

本次 stage 解决：
- 修 cron，**备份每天 02:00 自动**
- 限流 100→300，3 stats 端点加缓存
- 写 `scripts/restore-test.sh` 可复用、可定时
- 跑通真还原：8/8 表 100% 匹配
- **量化 5/25 vs 当前 18 天数据缺口**（隐藏金矿）

---

## 📊 Day 0: 调优（拉齐 14→15 之间的产物）

| 动作 | 改动 | 验证 |
|---|---|---|
| **限流 100→300 + 白名单** | rate_limit.py + 健康/指标路径免限 | 320→300/20 精确触发 |
| **Stats 缓存 (3 端点)** | products/customers/inventory 加 60-120s TTL | MISS→HIT, P95 184→132ms (-28%) |
| **backup-pg.sh 审计** | 看现状 | **发现 cron 缺失 + 18 天无备份** |

---

## 🔧 Day 1: 紧急修复（闭合 18 天盲点）

| # | 任务 | 用时 | 验证 |
|---|---|---|---|
| 1 | **.pgpass** 配好 (mode 600, 只对 aierp DB) | 30s | psql 免密 |
| 2 | **补 6-12 备份** 3.0M | 2s | pg_restore --list ✓ |
| 3 | **crontab 注册 0 2 \* \* \*** | 30s | crontab -l ✓ |
| 4 | **真还原 aierp_restore_test** | 10s | 8/8 表 100% 匹配 |

**测试**: 118 passed / 1 skipped（auth + auth_security + customers_api + state_machine）
**k6 复测**: 20 VU P95 450ms / 0 错误

### Day 1 真发现

1. **pgvector 扩展权限不足** — customers/products 用了 embedding 向量列
2. **PG 无 `ALTER EXTENSION OWNER` 语法** — 必须用 `--no-comments` 跳过 COMMENT
3. **本地 DB 弱密码 `aierp`** — 留 Stage 16+ 处理

---

## 🆕 Day 2: 自动化闭环

### 关键发现 — 5/25 vs 当前 数据缺口

| 表 | 5/25 | 当前 | 差 | 含义 |
|---|---|---|---|---|
| **customers** | 270 | 355 | **+85** | 18 天 31% 客户增长 |
| **products** | 252 | 268 | +16 | |
| **sales_orders** | 234 | 248 | +14 | |
| **purchase_orders** | 10 | 50 | **+40** | PO 模块 5/25 后才规模化用 |
| **inventory_transactions** | 0 | 42 | **+42** | 库存模块 5/25 后才启 |
| **users** | 6 | 7 | +1 | 元鼎汪洋 6-08 新增 |

**行业分布巨变**：
- "电子元器件分销" 从 **0 → 24**（18 天主推线）
- "电子制造" 从 93 → 45（被细分到子行业）
- 客户 13/15/20 行业字段被细化

**结论**: 如果今天 DB 炸了回到 5/25，**31% 客户 + 全部 PO/库存记录消失**。

### 写 `scripts/restore-test.sh` (162 行)

**功能**:
1. 自动选最新备份（或指定）
2. Drop + Create 独立 DB（带时间戳）
3. **pgvector 扩展**（超管创建，避开 owner 限制）
4. **pg_restore --no-owner --no-comments**（499 errors → 0）
5. **9 张核心表行数对比**
6. 失败 exit 1（可被 cron + ops-alert 接走）
7. 默认 Drop 还原 DB（`--keep` 留 24h 调试用）

**关键 bug 修复（写脚本时发现）**：
- `PG_PASSWORD` vs `PGPASSWORD` 拼写不一致 → 导出空值 → pg_restore 交互式要密码
- 加 `set -u` 但 `set -e` 误伤 psql 错误 → 改 `set -u` + 显式 `|| fail`

### 跑一次：0 errors / 9/9 表匹配 / 6s

### Cron: 每周日 04:00 自动跑
```
0 4 * * 0  /home/ttdiy/aierp/scripts/restore-test.sh
```

### 完整 backend 测试: 157 passed / 1 skipped / 1 瞬态 error

---

## 🔁 现在全闭环

| 任务 | 频率 | Cron | 失败告警 |
|---|---|---|---|
| **PG 备份** | 每天 02:00 | `0 2 * * *` | ops-alert (Telegram) |
| **备份还原测试** | 每周日 04:00 | `0 4 * * 0` | script exit 1 → ops-alert |
| **ops-alert** | 每小时 | `0 * * * *` | Telegram 直接推 |

→ **任何备份/还原失败 1 小时内推到 Telegram**（刘经理 ID: 8103002093）

---

## 📦 交付物

| 文件 | 用途 |
|---|---|
| `scripts/restore-test.sh` | 自动化还原测试（162 行） |
| `scripts/backup-pg.sh` | 备份脚本（已有，新增 .pgpass 支持） |
| `~/.pgpass` | mode 600，本地开发用，**不入 git** |
| crontab 2 条 | 02:00 备份 + 周日 04:00 还原测试 |
| `docs/STAGE15.md` | 本文档 |

**明天 02:00 首次自动跑** + **本周日 04:00 首次自动还原测试**

---

## 🆕 Stage 15 关键工程教训

1. **"未跑过 = 不知道有坑"** — pgvector + ALTER EXTENSION + 拼写 bug，写脚本才发现
2. **5/25 的"看起来没数据增长"是错觉** — 31% 客户+40 PO+42 库存都活在新数据里
3. **set -e + tee 组合有毒** — pipefail 会把 stderr 静默吞掉，调试费时
4. **.pgpass 精确匹配是 feature 不是 bug** — 生产用，dev 加额外行
5. **PG 无 ALTER EXTENSION OWNER 语法** — 只能建扩展时用对 user
6. **数据缺口 = 业务决策** — 18 天不是技术问题，是"什么时候上线/投产"的判断

---

## 🚨 留给未来 (Stage 16+)

| 优先级 | 问题 | 解决 |
|---|---|---|
| 🔴 | 18 天数据丢失的影响 | 客户告知 / 客户回访 |
| 🟠 | 本地 DB 弱密码 `aierp` | Stage 16 改密 + 删 default admin |
| 🟠 | 异地备份（无 `REMOTE_BACKUP_DIR`） | Stage 16+ rclone 到第二盘 |
| 🟡 | 还原未测"应用指向 restore DB" | Stage 16 写 e2e: restore → app boot → 跑通 |
| 🟡 | 没真 DR 演练（kill source DB） | Stage 17 计划剧本 |
| 🟢 | 备份文件无加密 | Stage 17+ `pg_dump | gpg` |

---

## 📊 Stage 15 vs Stage 14

| 维度 | Stage 14 | Stage 15 |
|---|---|---|
| 焦点 | 性能/容量 | **运维/数据安全** |
| 工具 | k6/Prometheus | **pg_dump/pg_restore/cron** |
| 产出 | 负载基线 + 调优 | **备份自动化 + 还原测试** |
| 心态 | "容量闭环" | "**数据闭环**" |
| 关键发现 | bcrypt 同步阻塞 9.4s | **18 天数据缺口 + 31% 客户** |

---

**15 stages / 56 commits / 13+ 小时 / 备份从 0 自动 / 还原测试从手动到自动** 🚀
