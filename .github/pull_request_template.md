## 摘要

<!-- 1-3 句话讲清楚这次改了什么、为什么 -->

## 改动类型

<!-- 勾选所有适用的 -->

- [ ] feat（新功能）
- [ ] fix（bug 修复）
- [ ] refactor（重构，不改外部行为）
- [ ] perf（性能优化）
- [ ] docs（文档）
- [ ] test（加测试）
- [ ] ci（CI / 脚本 / 工作流）
- [ ] chore（依赖 / 配置 / 杂项）

## 关联

<!-- 关联: Issue / Stage / 文档 -->

- Stage: <!-- Stage X Day Y -->
- 关联 Issue: <!-- #123 -->
- 文档: <!-- docs/STAGE*.md -->

## 改动清单

<!-- 列举核心改动，方便 reviewer 抓重点 -->

-
-
-

## 验证

<!-- 怎么验证这次改动是对的。CI 跑了什么 / 本地跑了什么 / 怎么手动验证 -->

- [ ] CI 全绿（lint / test / build / audit）
- [ ] 本地跑了 `pytest tests/...`
- [ ] 跑了 `k6 run loadtest/...`（如适用）
- [ ] 手动验证步骤：<!-- 描述 -->

## 风险 / 回滚

<!-- 评估影响面 + 怎么回滚 -->

- 影响面：<!-- 哪类用户 / 哪条流程 / 哪条数据 -->
- 回滚步骤：<!-- git revert / 关 flag / 删 cron -->

## Checklist

- [ ] 我读了自己写的 diff
- [ ] 没引入新警告（ruff / eslint / tsc）
- [ ] 没动 `master` 的 schema（迁移另开 PR）
- [ ] 没把 `.env` / `*.pem` / `*.dump` / `node_modules` 提交
- [ ] 文档同步更新（如有）
