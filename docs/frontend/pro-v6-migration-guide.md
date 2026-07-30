# Pro v6 迁移指南 (前端)

> 团队重新学习 Pro v6 技能 — 本文档作为参考和决策记录。

## 一、Pro v6 是什么？

Ant Design Pro v6 是 antd v6 + Umi Max 工具链 + ProComponents 的完整前端解决方案。

| 组件 | 替代 antd 组件 | 优势 |
|------|---------------|------|
| `ProForm` | `Form` + `Form.Item` | 声明式字段、submitter 内置、校验更简洁 |
| `ProTable` | `Table` | 内置 search/分页/toolbar、request 异步加载 |
| `ProCard` | `Card` | 支持 split/group/tabs 布局 |
| `ProLayout` | `Layout` (侧边栏 + header) | 完整后台布局 |
| `ProFormText` | `Form.Item` + `Input` | 简化字段声明 |
| `ProFormSelect` | `Form.Item` + `Select` | 内置 valueType |
| `ProFormDigit` | `Form.Item` + `InputNumber` | 数字字段 |
| `ProFormTextArea` | `Form.Item` + `Input.TextArea` | 多行文本 |
| `ProFormDatePicker` | `Form.Item` + `DatePicker` | 日期选择 |
| `ProFormSwitch` | `Form.Item` + `Switch` | 开关 |
| `ProFormSelect` | `Form.Item` + `Select` | 下拉 |

## 二、Pro v6 vs antd Form 迁移示例

### 1. 简单 Modal Form

**之前 (antd Form):**
```tsx
import { Form, Input, Select, message } from "antd";

const [form] = Form.useForm();

<Modal open={open} onOk={handleSave}>
  <Form form={form} layout="vertical">
    <Form.Item name="name" label="名称" rules={[{ required: true }]}>
      <Input />
    </Form.Item>
    <Form.Item name="type" label="类型">
      <Select options={[{ value: "a", label: "A" }]} />
    </Form.Item>
  </Form>
</Modal>
```

**之后 (ProForm):**
```tsx
import { App } from "antd";
import { ProForm, ProFormText, ProFormSelect } from "@ant-design/pro-components";

const { message } = App.useApp();
const [form] = ProForm.useForm();

<Modal open={open} onOk={handleSave}>
  <ProForm form={form} layout="vertical" submitter={false}>
    <ProFormText name="name" label="名称" rules={[{ required: true }]} />
    <ProFormSelect name="type" label="类型" options={[{ value: "a", label: "A" }]} />
  </ProForm>
</Modal>
```

**关键变化：**
1. `Form.useForm()` → `ProForm.useForm()`
2. `<Form>` → `<ProForm submitter={false}>` (Modal 已有 OK 按钮)
3. `<Form.Item name="x" label="y"><Input/></Form.Item>` → `<ProFormText name="x" label="y" />`
4. `message` 静态 import → `App.useApp()` 拿 message

### 2. 完整 Page Form (有 submit 按钮)

```tsx
<ProForm
  form={form}
  layout="vertical"
  onFinish={onFinish}
  initialValues={...}
  submitter={{
    render: () => [
      <Button key="submit" type="primary" htmlType="submit" loading={loading}>
        保存
      </Button>,
      <Button key="cancel" onClick={handleBack}>取消</Button>,
    ],
  }}
>
  <ProFormText name="title" label="标题" rules={[{ required: true }]} />
  <ProFormSelect name="status" label="状态" options={...} />
  <ProFormDatePicker name="deadline" label="截止日期" />
</ProForm>
```

### 3. ProTable

```tsx
<ProTable
  columns={columns}
  request={async (params) => {
    const resp = await client.get("/items", { params });
    return { data: resp.data.data.list, success: true, total: resp.data.data.total };
  }}
  search={{ labelWidth: "auto" }}
  pagination={{ pageSize: 20 }}
  toolBarRender={() => [<Button key="add">新增</Button>]}
  rowKey="id"
/>
```

## 三、ProForm 与 antd Form 兼容性

| 场景 | 兼容性 | 说明 |
|------|--------|------|
| `ProForm.useForm()` 传给 antd 子组件 | ✅ | FormInstance 类型相同 |
| `antd Form.useForm()` 传给 ProForm 子组件 | ✅ | 反向也兼容 |
| `Form.List` 作为 ProForm 子元素 | ✅ | ProForm 透传 FormContext |
| `Form.useFormInstance()` | ✅ | 父用 ProForm 时自动可用 |
| `Form.useFormInstance()` 父用 antd Form | ❌ | 需要父改 ProForm |

**结论：所有"不兼容"模式实际都兼容，只需让父级用 ProForm。**

## 四、何时使用 antd Form vs ProForm

| 场景 | 推荐 | 理由 |
|------|------|------|
| 新建页面 | **ProForm** | 与 Pro v6 生态一致 |
| 简单 Modal 编辑 | **ProForm** | submitter={false} + Modal onOk |
| 复杂 Form.List 动态字段 | **antd Form + Form.List** | ProFormList 语义不同 |
| 需要外部 form prop | **antd Form** | 类型兼容性更好 |
| AI Recognizer 等复杂子组件 | **antd Form** | 已稳定的依赖 |
| 修改旧页面 | **保留 antd Form** | 避免引入新 bug |

**原则：新代码用 ProForm，旧代码不强制迁移。**

## 五、迁移决策流程

1. 评估页面复杂度
2. 检查子组件依赖（Form.List? AI Recognizer? 外部 form prop?）
3. 简单的 Modal Form → 建议 ProForm
4. 复杂的 Page Form → 保留 antd Form
5. 每次只迁移 1 个文件，独立 PR
6. PR 标题清晰：`refactor(domain): migrate PageName to ProForm`

## 六、ProForm 提交器 (submitter) 三种用法

```tsx
// 1. 嵌入式 submit 按钮（最常见）
<ProForm submitter={{ searchConfig: { submitText: "保存", resetText: "重置" } }}>
  <ProFormText name="name" />
</ProForm>

// 2. 自定义 submitter（如 Modal 内用父按钮提交）
<ProForm submitter={false}>
  <ProFormText name="name" />
</ProForm>

// 3. 完整自定义 render
<ProForm
  submitter={{
    render: () => [
      <Button key="save" type="primary" htmlType="submit">保存</Button>,
      <Button key="reset" onClick={() => form.resetFields()}>重置</Button>,
    ],
  }}
>
  ...
</ProForm>
```

## 七、ProForm.useForm 与 Form API

```tsx
const [form] = ProForm.useForm();

// 全部 antd Form 方法都可用
form.setFieldsValue({...});
form.getFieldsValue();
form.getFieldValue("name");
form.setFieldValue("name", value);
form.resetFields();
form.validateFields();
form.submit();
```

## 八、message 和 notification 迁移

```tsx
// 之前
import { message } from "antd";
message.success("保存成功");
message.error("保存失败");

// 之后
import { App } from "antd";
const { message } = App.useApp();
message.success("保存成功");
message.error("保存失败");
```

## 九、推荐学习路径

1. 阅读本指南全部章节
2. 查看已迁移的 6 个 Sales 页面（OpportunityForm, QuotationForm, etc.）作为参考
3. 实践：在小页面（< 200 行）做 ProForm 迁移
4. 代码 review：每个 PR 都要明确说明"为什么用 ProForm 而不是 antd Form"
5. 团队内部分享踩坑经验

## 十、踩坑记录

### 坑 1：Form.useFormInstance 需父级 ProForm
- 子组件用 `Form.useFormInstance()` 时，**父组件必须是 ProForm**
- 解决：父改用 `ProForm.useForm()`

### 坑 2：ProFormList 语义不同
- ProFormList 字段名扁平化：`form.getFieldValue("items.0.name")` 不工作
- 解决：复杂动态字段保留 `Form.List` 作为 ProForm 子元素

### 坑 3：message 静态导入被 useEffect 清理
- antd 5+ message 改为动态注入，必须在 `<App>` 包裹下使用
- 解决：用 `App.useApp()` 拿 message

### 坑 4：columns 强制 any 类型
- ProTable columns 类型推断需要 ProColumns<T> 泛型
- 解决：`columns={columns as ProColumns<Item>[]}` 或 `as never`

## 决策记录

- **2026-07-29**：团队决定**新代码用 ProForm，旧代码保留 antd Form**。不再批量迁移现有页面。
- 原因：批量迁移造成 review 负担和回退循环。
- Pro v6 基础设施（路由、Layout、ProTable、ProCard、ProForm 在 6 个 Sales 页面）已就位。
