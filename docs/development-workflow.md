# AIERP 开发流程与规范

> 版本: 2.0 | 2026-06-22

---

## 1. 功能开发全生命周期

```
需求分析 → 计划 → TDD 开发 → 代码审查 → 提交 → PR → 合并
  │          │        │           │         │      │      │
  │          │     RED→GREEN     │         │      │      │
  │          │     →REFACTOR     │         │      │      │
  ↓          ↓        ↓           ↓         ↓      ↓      ↓
 Issue    Plan      Test-first  Code        Commit PR   Deploy
          doc       Tests pass  Review      msg   Review
```

### 1.1 需求分析

1. **GitHub Issue** — 所有需求从 Issue 开始
2. **brainstorming skill** — 技术方案选型前先做需求分析
3. **PRD 文档** — 复杂功能编写 PRD（9 章标准结构）

### 1.2 技术计划

1. `/plan` 或 `/plan-prd` — 生成实现计划
2. **多模型审查** — `/multi-plan` 协同 Codex + Gemini 分析
3. **产出**: `.claude/plan/<feature>.md`

### 1.3 TDD 开发

```
① RED      写测试，确认失败
② GREEN    最少代码让测试通过
③ REFACTOR 优化代码，保持绿色
④ COMMIT   每阶段 checkpoint commit
```

**Git 检查点**:
```bash
git commit -m "test: add reproducer for <feature>"   # RED
git commit -m "fix: <feature>"                        # GREEN
git commit -m "refactor: clean up <feature>"          # REFACTOR
```

### 1.4 代码审查

- **自动触发**: 写代码后立即用 `/code-review` 或 `code-reviewer` agent
- **安全检查**: `/security-scan` — 认证/用户输入/数据库查询代码
- **语言专项**: `python-reviewer`、`typescript-reviewer`、`fastapi-reviewer`

**审查清单**:
- [ ] 函数 < 50 行
- [ ] 文件 < 800 行
- [ ] 嵌套 < 4 层
- [ ] 无硬编码密钥
- [ ] 无 console.log
- [ ] 类型注解完整
- [ ] 测试覆盖 ≥ 80%

---

## 2. Git 工作流

### 2.1 分支策略

```
master          ← 主分支，随时可部署
  ├── feat/xxx  ← 功能分支
  ├── fix/xxx   ← 修复分支
  └── chore/xxx ← 维护分支
```

### 2.2 提交规范 (Conventional Commits)

```
<type>: <English description>

类型:
feat     — 新功能
fix      — Bug 修复
refactor — 重构（无行为变更）
docs     — 文档
test     — 测试
chore    — 维护、依赖
perf     — 性能优化
style    — 格式化
ci       — CI/CD
```

**规则**: 首行 ≤ 72 字符，英文。中文摘要可接受。不混合重构+功能。

### 2.3 Pull Request 流程

```bash
git checkout -b feat/my-feature
# ... 开发 + 测试 + 提交 ...
git push -u origin feat/my-feature
gh pr create --title "feat: xxx" --body "Close #42"
```

**PR 描述模板**:
```markdown
## Summary
[用户可见变更]

## Changes
- `file.py` — 描述

## Verification
- `make test`: NNNN passed
- `make lint`: clean

Close #issue-number
```

### 2.4 提交前检查

```bash
make lint          # ruff + mypy + tsc
make test          # pytest + vitest
make security-check # pip-audit + npm audit
```

---

## 3. 测试策略

### 3.1 测试金字塔

```
        /\
       /E2E\       Playwright — 关键用户流
      /------\
     /Integration\  httpx + SQLite — API 端点 + 数据库
    /------------\
   /   Unit Tests  \  pytest + vitest — 纯函数/状态机
  /----------------\
```

### 3.2 覆盖率要求

| 层级 | 目标 | 工具 |
|------|------|------|
| 单元测试 | ≥ 80% | pytest, vitest |
| 集成测试 | ≥ 80% | httpx + AsyncClient |
| 状态机 | 100% (16 实体) | 纯逻辑测试 |
| 财务计算 | 100% | Decimal 精确断言 |

### 3.3 测试命名

```python
# 后端
def test_contract_draft_to_signed():
    """draft → signed 转换允许"""
    
def test_contract_active_to_expired_is_terminal():
    """expired 状态不可再转换"""

# 前端  
test('renders #undefined when contract id is missing', () => {})
test('shows error alert when API returns 500', () => {})
```

### 3.4 运行测试

```bash
make test                  # 全部
make test-backend          # 后端
make test-frontend         # 前端
pytest tests/test_file.py::test_name -v  # 单个
```

---

## 4. 编码规范

### 4.1 Python (PEP 8 + 项目扩展)

```python
# 类型注解 — 所有函数签名
async def list_contracts(
    db: AsyncSession,
    *,
    page: int = 1,
    customer_id: int | None = None,
) -> dict:
    ...

# Decimal 用于金额，永不 float
from decimal import Decimal
amount = Decimal(str(value))

# 状态机 — Enum + transition map
CONTRACT_TRANSITIONS: dict[str, set[str]] = {
    "draft": {"signed", "cancelled"},
}
```

### 4.2 TypeScript / React

```typescript
// Props interface — 命名导出
interface ContractFormProps {
  id?: number;
  onSave: (data: ContractData) => void;
}

// API 层 — 集中在 frontend/src/api/
export const getContracts = (params: Record<string, unknown>) =>
  client.get<APIResponse<PageData<Contract>>>("/contracts", { params });

// 懒加载 — 所有页面
const ContractList = lazy(() => import("./pages/sales/ContractList"));
```

### 4.3 文件组织

```
backend/
├── app/
│   ├── api/v1/         # 路由（薄层 — 只做解析+调用+返回）
│   ├── services/       # 业务逻辑（厚层 — 所有权重在这里）
│   ├── models/         # SQLAlchemy ORM
│   ├── schemas/        # Pydantic 请求/响应
│   └── domain/states/  # 状态机（纯逻辑，无框架依赖）
│
frontend/src/
├── api/                # 单一 API 层
├── pages/<domain>/     # 按业务域组织
├── ui/                 # 共享组件库
└── store/              # Zustand 状态管理
```

---

## 5. 架构模式

### 5.1 分层架构

```
API Layer (routes)      ← 薄层，解析 → 调用 → 返回
    ↓
Service Layer           ← 业务逻辑，跨聚合根操作
    ↓
Domain Layer            ← 状态机，领域事件，纯逻辑
    ↓
Model Layer (ORM)       ← 数据持久化
```

### 5.2 状态机模式

```python
# 1. 定义转换
TRANSITIONS = {"draft": {"signed"}, "signed": {"active"}}

# 2. 守卫函数
def assert_can_transition(current, target):
    if target not in TRANSITIONS[current]:
        raise InvalidStateTransition(...)

# 3. 服务层调用
if "status" in data and data["status"] != obj.status:
    assert_can_transition(obj.status, data["status"])
```

### 5.3 仓库/缓存模式

```python
# Versioned cache — 写操作自动失效
await cache_get_versioned("contracts:list", cache_key)
await cache_set_versioned("contracts:list", cache_key, data, ttl=300)
await cache_bump_version("contracts:list")  # 写操作后
```

### 5.4 API 响应格式

```json
{
  "code": 0,
  "msg": "success",
  "data": { ... },
  "request_id": "req_xxx"
}
```

---

## 6. 质量保障

### 6.1 工程底线（不可协商）

| 规则 | 违反后果 |
|------|---------|
| 状态机必定义 Enum + transition map | 不可合并 |
| 金额必用 Decimal，不可 float | 不可合并 |
| 服务层持业务逻辑，路由保持薄 | 不可合并 |
| 软删除（deleted_at）所有实体 | 不可合并 |
| RBAC 每路由声明权限 | 不可合并 |
| 请求 ID 端到端追踪 | 不可合并 |

### 6.2 常用命令速查

```bash
make dev                 # 启动开发环境 (:8080 + :3002)
make test                # 全部测试
make lint                # 代码检查
make build               # 构建
make db-reset            # 重建数据库
docker compose up -d     # 启动 PostgreSQL + Redis
```
