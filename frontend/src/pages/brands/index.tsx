import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Table, Button, Input, Space, message, Card, Modal, Form, Tag, Popconfirm, Typography, Select, Tabs, Row, Col, Switch } from "antd";
import { PlusOutlined, ReloadOutlined, EditOutlined, DeleteOutlined, ImportOutlined } from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import { getBrands, createBrand, updateBrand, deleteBrand, importBrandFromText } from "../../api";
import type { Brand } from "../../types";

const { Text } = Typography;

const STATUS_OPTIONS = [
  { label: "启用", value: "active" },
  { label: "停用", value: "inactive" },
  { label: "冻结", value: "frozen" },
];
const LEVEL_OPTIONS = [
  { label: "A级", value: "A" },
  { label: "B级", value: "B" },
  { label: "C级", value: "C" },
];
const TYPE_OPTIONS = [
  { label: "自有品牌", value: "own_brand" },
  { label: "代理品牌", value: "agency" },
  { label: "OEM", value: "oem" },
];
const LIFECYCLE_OPTIONS = [
  { label: "Active", value: "active" },
  { label: "NRND", value: "nrnd" },
  { label: "EOL", value: "eol" },
];
const RISK_OPTIONS = [
  { label: "低", value: "low" },
  { label: "中", value: "medium" },
  { label: "高", value: "high" },
  { label: "严重", value: "critical" },
];
const AUTH_OPTIONS = [
  { label: "已授权", value: "authorized" },
  { label: "未授权", value: "unauthorized" },
  { label: "未知", value: "unknown" },
];
const ROHS_OPTIONS = [
  { label: "合规", value: "compliant" },
  { label: "不合规", value: "non_compliant" },
  { label: "豁免", value: "exempt" },
  { label: "未知", value: "unknown" },
];

const statusColor: Record<string, string> = { active: "green", inactive: "orange", frozen: "red" };
const statusLabel: Record<string, string> = { active: "启用", inactive: "停用", frozen: "冻结" };
const levelColor: Record<string, string> = { A: "red", B: "blue", C: "default" };
const typeLabel: Record<string, string> = { own_brand: "自有", agency: "代理", oem: "OEM" };

export default function BrandList() {
  const [data, setData] = useState<Brand[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<Brand | null>(null);
  const [form] = Form.useForm();
  const [submitting, setSubmitting] = useState(false);
  const [importOpen, setImportOpen] = useState(false);
  const [importText, setImportText] = useState("");
  const [importLoading, setImportLoading] = useState(false);
  const [filterStatus, setFilterStatus] = useState<string | undefined>();
  const [filterLevel, setFilterLevel] = useState<string | undefined>();
  const [filterType, setFilterType] = useState<string | undefined>();
  const navigate = useNavigate();

  const fetch = async (q = search) => {
    setLoading(true);
    try {
      const resp = await getBrands(q ? { q } : undefined);
      let list = resp.data.data as Brand[];
      if (filterStatus) list = list.filter((b) => b.status === filterStatus);
      if (filterLevel) list = list.filter((b) => b.level === filterLevel);
      if (filterType) list = list.filter((b) => b.brand_type === filterType);
      setData(list);
    } catch { message.error("加载品牌失败"); }
    finally { setLoading(false); }
  };

  useEffect(() => { fetch(); }, [filterStatus, filterLevel, filterType]);

  const openCreate = () => {
    setEditing(null);
    form.resetFields();
    form.setFieldsValue({ status: "active", is_automotive: false });
    setModalOpen(true);
  };

  const openEdit = (b: Brand) => {
    setEditing(b);
    form.setFieldsValue(b);
    setModalOpen(true);
  };

  const handleSubmit = async () => {
    setSubmitting(true);
    try {
      if (editing) {
        await updateBrand(editing.id, form.getFieldsValue());
        message.success("更新成功");
      } else {
        await createBrand(form.getFieldsValue());
        message.success("创建成功");
      }
      setModalOpen(false);
      fetch();
    } catch { message.error("操作失败"); }
    finally { setSubmitting(false); }
  };

  const handleDelete = async (id: number) => {
    try {
      await deleteBrand(id);
      message.success("删除成功");
      fetch();
    } catch { message.error("删除失败"); }
  };

  const handleImport = async () => {
    setImportLoading(true);
    try {
      const resp = await importBrandFromText(importText, true);
      const d = resp.data.data as unknown as Record<string, unknown>;
      if (d.created_id) {
        message.success(`已创建品牌: ${d.name}`);
        navigate(`/brands/${d.created_id}`);
      } else {
        message.success(`已解析: ${d.name}`);
      }
      setImportOpen(false);
      setImportText("");
    } catch { message.error("导入失败"); }
    finally { setImportLoading(false); }
  };

  const columns: ColumnsType<Brand> = [
    { title: "ID", dataIndex: "id", width: 50 },
    { title: "编码", dataIndex: "code", width: 80, render: (v) => v || "-" },
    {
      title: "名称", dataIndex: "name", width: 150,
      render: (v, r) => <a onClick={() => navigate(`/brands/${r.id}`)}>{v}</a>,
    },
    { title: "中文名", dataIndex: "name_cn", width: 100, render: (v) => v || "-" },
    {
      title: "状态", dataIndex: "status", width: 70,
      render: (v) => <Tag color={statusColor[v] || "default"}>{statusLabel[v] || v}</Tag>,
    },
    {
      title: "类型", dataIndex: "brand_type", width: 70,
      render: (v) => v ? <Tag>{typeLabel[v] || v}</Tag> : "-",
    },
    {
      title: "等级", dataIndex: "level", width: 60,
      render: (v) => v ? <Tag color={levelColor[v]}>{v}级</Tag> : "-",
    },
    { title: "分类", dataIndex: "category", width: 90, render: (v) => v || "-" },
    { title: "负责人", dataIndex: "owner", width: 80, render: (v) => v || "-" },
    {
      title: "创建时间", dataIndex: "created_at", width: 90,
      render: (v: string) => v?.slice(0, 10) || "-",
    },
    {
      title: "操作", key: "action", width: 120, fixed: "right",
      render: (_: unknown, r) => (
        <Space>
          <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(r)}>编辑</Button>
          <Popconfirm title="确认删除？" onConfirm={() => handleDelete(r.id)}>
            <Button size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <Card
        title="品牌管理"
        extra={
          <Space wrap>
            <Input.Search
              placeholder="搜索品牌" allowClear
              value={search} onChange={(e) => setSearch(e.target.value)}
              onSearch={(v) => fetch(v)} style={{ width: 180 }}
            />
            <Select placeholder="状态" allowClear style={{ width: 80 }} value={filterStatus} onChange={setFilterStatus} options={STATUS_OPTIONS} />
            <Select placeholder="等级" allowClear style={{ width: 80 }} value={filterLevel} onChange={setFilterLevel} options={LEVEL_OPTIONS} />
            <Select placeholder="类型" allowClear style={{ width: 100 }} value={filterType} onChange={setFilterType} options={TYPE_OPTIONS} />
            <Button icon={<ReloadOutlined />} onClick={() => fetch()}>刷新</Button>
            <Button icon={<ImportOutlined />} onClick={() => setImportOpen(true)}>AI 导入</Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>新增</Button>
          </Space>
        }
      >
        <Table
          rowKey="id" columns={columns} dataSource={data}
          loading={loading} size="small" pagination={false}
          scroll={{ x: 1100 }}
        />
      </Card>

      <Modal
        title={editing ? "编辑品牌" : "新增品牌"}
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={handleSubmit}
        confirmLoading={submitting}
        okText={editing ? "保存" : "创建"}
        width={720}
      >
        <Form form={form} layout="vertical">
          <Tabs
            defaultActiveKey="basic"
            items={[
              {
                key: "basic", label: "基础信息",
                children: (
                  <Row gutter={16}>
                    <Col span={8}>
                      <Form.Item name="code" label="编码"><Input placeholder="唯一编码" /></Form.Item>
                    </Col>
                    <Col span={16}>
                      <Form.Item name="name" label="名称" rules={[{ required: true, message: "请输入品牌名称" }]}>
                        <Input placeholder="如 TI / STMicroelectronics" />
                      </Form.Item>
                    </Col>
                    <Col span={12}>
                      <Form.Item name="name_cn" label="中文名"><Input placeholder="如 德州仪器" /></Form.Item>
                    </Col>
                    <Col span={12}>
                      <Form.Item name="short_name" label="简称"><Input placeholder="系统显示用" /></Form.Item>
                    </Col>
                    <Col span={8}>
                      <Form.Item name="status" label="状态">
                        <Select options={STATUS_OPTIONS} />
                      </Form.Item>
                    </Col>
                    <Col span={8}>
                      <Form.Item name="brand_type" label="类型">
                        <Select placeholder="选择类型" allowClear options={TYPE_OPTIONS} />
                      </Form.Item>
                    </Col>
                    <Col span={8}>
                      <Form.Item name="category" label="分类"><Input placeholder="半导体/被动器件" /></Form.Item>
                    </Col>
                    <Col span={8}>
                      <Form.Item name="logo" label="Logo URL"><Input placeholder="https://..." /></Form.Item>
                    </Col>
                    <Col span={24}>
                      <Form.Item name="description" label="品牌介绍"><Input.TextArea rows={2} /></Form.Item>
                    </Col>
                    <Col span={24}>
                      <Form.Item name="notes" label="备注"><Input.TextArea rows={2} /></Form.Item>
                    </Col>
                  </Row>
                ),
              },
              {
                key: "business", label: "商业信息",
                children: (
                  <Row gutter={16}>
                    <Col span={8}>
                      <Form.Item name="level" label="品牌等级"><Select placeholder="选择等级" allowClear options={LEVEL_OPTIONS} /></Form.Item>
                    </Col>
                    <Col span={8}>
                      <Form.Item name="positioning" label="品牌定位">
                        <Select placeholder="选择定位" allowClear options={[
                          { label: "高端", value: "high" }, { label: "中端", value: "mid" }, { label: "低端", value: "low" },
                        ]} />
                      </Form.Item>
                    </Col>
                    <Col span={8}>
                      <Form.Item name="owner" label="负责人"><Input /></Form.Item>
                    </Col>
                    <Col span={12}>
                      <Form.Item name="product_lines" label="产品线"><Input.TextArea rows={2} placeholder="MCU, MOS, 连接器..." /></Form.Item>
                    </Col>
                    <Col span={12}>
                      <Form.Item name="target_markets" label="目标市场"><Input.TextArea rows={2} placeholder="工业、医疗、车规..." /></Form.Item>
                    </Col>
                    <Col span={12}>
                      <Form.Item name="website" label="官网"><Input placeholder="https://..." /></Form.Item>
                    </Col>
                  </Row>
                ),
              },
              {
                key: "supply", label: "供应链",
                children: (
                  <Row gutter={16}>
                    <Col span={12}>
                      <Form.Item name="manufacturer_name" label="原厂名称"><Input /></Form.Item>
                    </Col>
                    <Col span={12}>
                      <Form.Item name="supplier_id" label="关联供应商"><Input type="number" /></Form.Item>
                    </Col>
                    <Col span={8}>
                      <Form.Item name="authorization_status" label="授权状态"><Select placeholder="选择" allowClear options={AUTH_OPTIONS} /></Form.Item>
                    </Col>
                    <Col span={8}>
                      <Form.Item name="lifecycle_stage" label="生命周期"><Select placeholder="选择" allowClear options={LIFECYCLE_OPTIONS} /></Form.Item>
                    </Col>
                    <Col span={8}>
                      <Form.Item name="is_automotive" label="车规" valuePropName="checked"><Switch /></Form.Item>
                    </Col>
                    <Col span={6}>
                      <Form.Item name="moq" label="MOQ"><Input type="number" /></Form.Item>
                    </Col>
                    <Col span={6}>
                      <Form.Item name="lead_time_days" label="交期(天)"><Input type="number" /></Form.Item>
                    </Col>
                    <Col span={6}>
                      <Form.Item name="risk_level" label="风险等级"><Select placeholder="选择" allowClear options={RISK_OPTIONS} /></Form.Item>
                    </Col>
                    <Col span={6}>
                      <Form.Item name="rohs_status" label="RoHS"><Select placeholder="选择" allowClear options={ROHS_OPTIONS} /></Form.Item>
                    </Col>
                  </Row>
                ),
              },
              {
                key: "ai", label: "AI参数",
                children: (
                  <Row gutter={16}>
                    <Col span={24}>
                      <Form.Item name="ai_keywords" label="AI关键词"><Input.TextArea rows={2} placeholder="逗号分隔，用于AI搜索匹配" /></Form.Item>
                    </Col>
                    <Col span={12}>
                      <Form.Item name="risk_score" label="风险评分 (0-100)"><Input type="number" min={0} max={100} /></Form.Item>
                    </Col>
                    <Col span={12}>
                      <Form.Item name="alternative_brands" label="替代品牌"><Input.TextArea rows={2} placeholder="逗号分隔品牌名或编码" /></Form.Item>
                    </Col>
                  </Row>
                ),
              },
            ]}
          />
        </Form>
      </Modal>

      <Modal
        title="AI 品牌导入"
        open={importOpen}
        onCancel={() => setImportOpen(false)}
        onOk={handleImport}
        confirmLoading={importLoading}
        okText="导入"
      >
        <Text>粘贴品牌描述文本（公司介绍、官网About、供应商目录等），AI 自动提取品牌信息：</Text>
        <Input.TextArea
          rows={6} value={importText}
          onChange={(e) => setImportText(e.target.value)}
          placeholder="例如：意法半导体 (STMicroelectronics) 是全球领先的半导体公司，专注于MCU、电源管理、传感器等产品线..."
          style={{ marginTop: 8 }}
        />
      </Modal>
    </div>
  );
}
