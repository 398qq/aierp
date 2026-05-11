# 005-phase7-documents-dashboards

## 1. 概述

Phase 7 为 AIERP 提供三大能力：文档管理（J）、增强仪表板（K）、批量导入导出（L）。

### 范围
- **J. 文档管理** — 附件上传/下载关联到任意业务实体
- **K. 增强仪表板** — 可自定义的 KPI 卡片 + 拖拽布局
- **L. 批量导入导出** — 全实体 Excel 模板导入/导出

## 2. 目标

| 目标 | 衡量标准 |
|------|---------|
| 文档附件覆盖率 | 客户、产品、订单、采购单均可上传附件 |
| 仪表板可定制 | 用户可添加/删除/排列 KPI 卡片 |
| 导入导出 | 6 个以上实体支持 Excel 导入/导出 |

## 3. 用户故事

- 作为销售，我希望在客户详情页上传合同文件
- 作为采购，我希望在采购单上附供应商报价单
- 作为管理者，我希望定制仪表板只显示我关心的指标
- 作为运营，我希望批量导入客户和产品数据

## 4. 功能需求

### J. 文档管理
- Document 模型：id, entity_type, entity_id, filename, file_path, file_size, mime_type, uploaded_by
- POST /api/v1/documents/upload — 上传文件
- GET /api/v1/documents?entity_type=X&entity_id=Y — 列表
- GET /api/v1/documents/{id}/download — 下载
- DELETE /api/v1/documents/{id} — 删除
- 前端：通用附件面板组件，嵌入客户/产品/订单详情页

### K. 增强仪表板
- DashboardWidget 模型：id, user_id, widget_type, config, position
- GET/PUT /api/v1/dashboard/widgets — 用户仪表板配置
- GET /api/v1/dashboard/kpi — 实时 KPI 数据
- 前端：可拖拽卡片布局（react-grid-layout）

### L. 批量导入导出
- GET /api/v1/export/{entity}?format=xlsx — 导出模板
- POST /api/v1/import/{entity} — 导入 Excel
- 实体：customers, products, suppliers, purchase_orders, sales_orders, invoices

## 5. 非功能需求

- 文件上传限制 10MB，支持 pdf/docx/xlsx/jpg/png
- 仪表板 KPI 缓存 5 分钟
- 导入每批最多 1000 行

## 6. 数据模型

```sql
CREATE TABLE documents (
    id SERIAL PRIMARY KEY,
    entity_type VARCHAR(50) NOT NULL,
    entity_id INTEGER NOT NULL,
    filename VARCHAR(500) NOT NULL,
    file_path VARCHAR(1000) NOT NULL,
    file_size INTEGER NOT NULL,
    mime_type VARCHAR(100),
    uploaded_by INTEGER REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE TABLE dashboard_widgets (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    widget_type VARCHAR(50) NOT NULL,
    title VARCHAR(200),
    config JSON DEFAULT '{}',
    position_x INTEGER DEFAULT 0,
    position_y INTEGER DEFAULT 0,
    width INTEGER DEFAULT 3,
    height INTEGER DEFAULT 2,
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);
```

## 7. API 设计

| Method | Path | Description |
|--------|------|-------------|
| POST | /api/v1/documents/upload | Upload attachment |
| GET | /api/v1/documents | List attachments for entity |
| GET | /api/v1/documents/{id}/download | Download file |
| DELETE | /api/v1/documents/{id} | Delete attachment |
| GET | /api/v1/dashboard/widgets | Get user widgets |
| PUT | /api/v1/dashboard/widgets | Save widget layout |
| GET | /api/v1/dashboard/kpi | Get KPI data |
| GET | /api/v1/export/{entity} | Export Excel |
| POST | /api/v1/import/{entity} | Import Excel |

## 8. UI/UX 设计

- 附件面板：列表 + 上传按钮，点击下载，确认删除
- 仪表板：卡片网格，可拖拽调整位置，右上角 "+" 添加卡片
- 导入：上传 Excel → 预览 → 确认导入 → 结果反馈

## 9. 测试策略

- 文档上传/下载/删除 CRUD 测试
- 仪表板 KPI 数据准确性测试
- 导入验证：重复 SKU、必填字段缺失、格式错误
- 权限：文档操作需登录，仪表板需登录
- 文件大小限制测试
