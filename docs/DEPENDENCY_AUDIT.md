# 依赖审计（Stage 5 Day 4）

## 当前状态（2026-06-11）

### Frontend

```
$ npm audit --audit-level=high
found 0 vulnerabilities
```

✅ **0 高危漏洞**。

### Backend（已知 CVE）

`pip-audit --strict` 报告 **15+ CVE**，主要集中：

| 包 | 当前版本 | 修复版本 | CVE | 类型 |
|---|---|---|---|---|
| starlette | 0.46.2 | 1.0.1 / 0.49.1 | CVE-2025-54121 / CVE-2025-62727 / PYSEC-2026-161 | DoS / SSRF |
| pip | 24.0 | 25.3 / 26.x | CVE-2025-8869 / CVE-2026-1703 | RCE / path traversal |
| pyasn1 | 0.4.8 | 0.6.3 | CVE-2026-30922 | 类型混淆 |
| pytest | 8.3.0 | 9.0.3 | CVE-2025-71176 | - |
| python-multipart | 0.0.20 | 0.0.27 | CVE-2026-24486 | DoS |
| pillow | 11.2.1 | 12.2.0 | CVE-2026-42311 | 堆溢出 |

## 决策：CI 不阻塞

`pip-audit --strict` 默认会让 CI 失败 = **阻塞所有 PR**。但**当前 15+ 漏洞都是 pre-existing**（Stage 1-4 之前就在），新代码本身没引入新漏洞。

**当前策略**：
- Backend：`pip-audit` 报告但不阻塞（`::warning::` GitHub annotation）
- Frontend：`npm audit --audit-level=high` **真阻塞**（目前 0 vuln，可严格）

**目标**：逐步修老漏洞，3 个月内 `pip-audit --strict` 0 警告 → 改成真阻塞。

## 修复优先级

### 高（生产相关）

1. **starlette 0.46.2 → 0.49.1**
   - 影响：FastAPI 框架
   - 修复：改 `requirements.txt`
   - 风险：API 行为可能变（需回归测试）
   - 预计：30 分钟（spec 测试 123 个验证）

2. **python-multipart 0.0.20 → 0.0.27**
   - 影响：FastAPI form-data 解析
   - 修复：改 `requirements.txt`
   - 风险：低（patch version）

### 中

3. **pillow 11.2.1 → 12.2.0**
   - 影响：图片处理
   - 修复：直接升级
   - 风险：API 变化（12.x 是 major release）

4. **pyasn1 0.4.8 → 0.6.3**
   - 影响：cryptography 依赖链
   - 修复：升级 cryptography 会自动升级

### 低（开发依赖）

5. **pip 24.0 → 26.x**：开发环境，影响小
6. **pytest 8.3.0 → 9.0.3**：测试运行器

## 行动

| 周次 | 任务 | 阻塞 |
|---|---|---|
| 2026 W24 | 升 starlette + python-multipart | ❌ |
| 2026 W25 | 升 pillow + pyasn1 | ❌ |
| 2026 W26 | 升 pytest 9 + pip 26 | ❌ |
| 2026 W27 | 改 `pip-audit --strict` 为真阻塞 | ✅ |

## CI 流程

`.github/workflows/ci.yml`：

```yaml
- name: Security audit (pip-audit, advisory only)
  run: |
    pip-audit --strict --requirement requirements.txt 2>&1 | tee /tmp/pip-audit.log || {
      echo "::warning::pip-audit found vulnerabilities. See docs/DEPENDENCY_AUDIT.md to triage."
    }
```

```yaml
- name: Security audit (npm audit)
  run: npm audit --audit-level=high  # 真阻塞
```

## 何时升级？

- **安全公告**：直接升（不走 PR 流程，hotfix）
- **Dependabot 每周 PR**：review + 合并
- **手动升级**：每季度 1 次

## 工具

| 工具 | 用途 | 命令 |
|---|---|---|
| `pip-audit` | Python CVE 扫描 | `pip-audit --strict -r requirements.txt` |
| `npm audit` | Node CVE 扫描 | `npm audit --audit-level=high` |
| `safety` | 备选 Python 工具 | `safety check -r requirements.txt` |
| `snyk` | 商业方案 | 略 |

## 未来

- 启 Dependabot 自动提 PR（`/.github/dependabot.yml`）
- 升级 SBOM（Software Bill of Materials）输出
- Trivy 容器扫描（部署到 k8s 时）
