import { useEffect, useRef, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { Table, Button, Input, Space, Tag, message, Modal, Form, Select, Popconfirm, Card, Row, Col } from "antd";
import { PlusOutlined, SearchOutlined, ThunderboltOutlined, FileTextOutlined, EditOutlined, DeleteOutlined } from "@ant-design/icons";
import { getProducts, createProduct, updateProduct, deleteProduct, getBrands, aiParseProduct, aiParseBom } from "../../api";
import type { Product, Brand } from "../../types";

export default function ProductList() {
  const [data, setData] = useState<Product[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [q, setQ] = useState("");
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<Product | null>(null);
  const [brands, setBrands] = useState<Brand[]>([]);
  const [aiModalOpen, setAiModalOpen] = useState(false);
  const [aiText, setAiText] = useState("");
  const [aiParsing, setAiParsing] = useState(false);
  const [bomModalOpen, setBomModalOpen] = useState(false);
  const [bomText, setBomText] = useState("");
  const [bomParsing, setBomParsing] = useState(false);
  const [form] = Form.useForm();
  const debounceRef = useRef<ReturnType<typeof setTimeout>>(undefined);
  const navigate = useNavigate();

  // Column widths state
  const [widths, setWidths] = useState<Record<string, number>>({
    sku: 120,
    name: 220,
    category: 80,
    package_type: 90,
    specs: 180,
    unit: 60,
    brand_name: 100,
  });

  // Resize state
  const resizing = useRef<{ key: string; startX: number; startW: number } | null>(null);
  const tableRef = useRef<HTMLDivElement>(null);

  const onHeaderMouseDown = useCallback((e: React.MouseEvent<HTMLDivElement>, key: string, currentWidth: number) => {
    e.preventDefault();
    e.stopPropagation();
    resizing.current = { key, startX: e.clientX, startW: currentWidth };
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
    document.body.classList.add("col-resizing");
  }, []);

  useEffect(() => {
    const onMouseMove = (e: MouseEvent) => {
      if (!resizing.current) return;
      const delta = e.clientX - resizing.current.startX;
      const next = Math.max(40, resizing.current.startW + delta);
      setWidths(prev => ({ ...prev, [resizing.current!.key]: next }));
    };
    const onMouseUp = () => {
      if (!resizing.current) return;
      resizing.current = null;
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
      document.body.classList.remove("col-resizing");
    };
    document.addEventListener("mousemove", onMouseMove);
    document.addEventListener("mouseup", onMouseUp);
    return () => {
      document.removeEventListener("mousemove", onMouseMove);
      document.removeEventListener("mouseup", onMouseUp);
    };
  }, []);

  const fetch = async (p = page, search = q) => {
    setLoading(true);
    try {
      const params: Record<string, unknown> = { page: p, page_size: 20 };
      if (search) params.q = search;
      const resp = await getProducts(params);
      setData(resp.data.data.list);
      setTotal(resp.data.data.total);
    } catch {
      message.error("加载产品列表失败");
    } finally {
      setLoading(false);
    }
  };

  const loadBrands = async () => {
    try {
      const r = await getBrands();
      setBrands((r.data.data || []) as Brand[]);
    } catch (err: any) {
      console.error("加载品牌失败", err?.response?.status, err?.message);
    }
  };

  useEffect(() => { loadBrands(); }, []);
  useEffect(() => { fetch(); }, [page]);

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => { setPage(1); fetch(1, q); }, 350);
    return () => { if (debounceRef.current) clearTimeout(debounceRef.current); };
  }, [q]);

  const openCreate = () => { setEditing(null); form.resetFields(); loadBrands(); setModalOpen(true); };
  const openEdit = (p: Product) => { setEditing(p); form.setFieldsValue(p); loadBrands(); setModalOpen(true); };

  const handleSave = async (values: Record<string, unknown>) => {
    try {
      if (editing) { await updateProduct(editing.id, values); message.success("已更新"); }
      else { await createProduct(values); message.success("已创建"); }
      setModalOpen(false);
      fetch();
    } catch { message.error(editing ? "更新失败" : "创建失败"); }
  };

  const handleDelete = async (id: number) => {
    try { await deleteProduct(id); message.success("已删除"); fetch(); }
    catch { message.error("删除失败"); }
  };

  const handleAiParse = async () => {
    if (!aiText.trim()) return;
    setAiParsing(true);
    try {
      const resp = await aiParseProduct(aiText.trim());
      const parsed = resp.data.data as Record<string, unknown>;
      const specsStr = parsed.specs && typeof parsed.specs === "object"
        ? JSON.stringify(parsed.specs) : String(parsed.specs || "");
      let brandId: number | undefined;
      const brandName = String(parsed.brand_name || "").toLowerCase();
      if (brandName) {
        const match = brands.find(b =>
          b.name.toLowerCase().includes(brandName) || (b.name_cn || "").toLowerCase().includes(brandName)
        );
        if (match) brandId = match.id;
      }
      form.setFieldsValue({
        name: parsed.name, sku: parsed.sku || undefined,
        category: parsed.category || undefined, package_type: parsed.package_type || undefined,
        specs: specsStr, unit: parsed.unit || undefined, brand_id: brandId,
        notes: parsed.description || undefined,
      });
      setAiModalOpen(false); setAiText(""); setModalOpen(true);
      message.success("AI 解析完成，请确认后保存");
    } catch { message.error("AI 解析失败"); }
    finally { setAiParsing(false); }
  };

  const handleBomParse = async () => {
    if (!bomText.trim()) return;
    setBomParsing(true);
    try {
      const resp = await aiParseBom(bomText.trim());
      const items = (resp.data.data as { items: Record<string, unknown>[] }).items || [];
      let created = 0;
      for (const item of items) {
        try {
          await createProduct({
            name: String(item.mfr_pn || item.description || "未知型号"),
            sku: String(item.mfr_pn || item.customer_pn || ""),
            category: String(item.category || ""),
            package_type: String(item.package || ""),
            specs: String(item.description || ""),
            notes: `BOM导入: 客户料号=${item.customer_pn || ""} 位号=${item.reference || ""} 用量=${item.quantity || ""}`,
          });
          created++;
        } catch { /* skip */ }
      }
      setBomModalOpen(false); setBomText("");
      message.success(`BOM 解析完成，成功创建 ${created}/${items.length} 个产品`);
      fetch(1);
    } catch { message.error("BOM 解析失败"); }
    finally { setBomParsing(false); }
  };

  const makeHeader = (title: string, key: string, w: number) => (
    <div
      style={{
        width: w,
        position: "relative",
        display: "flex",
        alignItems: "center",
        cursor: "col-resize",
        userSelect: "none",
        height: "100%",
      }}
    >
      <span style={{ flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
        {title}
      </span>
      <div
        style={{
          position: "absolute",
          right: 0,
          top: 0,
          width: 4,
          height: "100%",
          cursor: "col-resize",
          zIndex: 10,
          background: "transparent",
        }}
        className="col-resize-handle"
        data-key={key}
        onMouseDown={(e) => { e.preventDefault(); e.stopPropagation(); onHeaderMouseDown(e, key, w); }}
      />
    </div>
  );

  const columns = [
    { title: makeHeader("SKU", "sku", widths.sku), dataIndex: "sku", key: "sku", width: widths.sku },
    { title: makeHeader("产品名称", "name", widths.name), dataIndex: "name", key: "name", width: widths.name, render: (text: string, r: Product) => <a onClick={() => navigate(`/products/${r.id}`)}>{text}</a> },
    { title: makeHeader("分类", "category", widths.category), dataIndex: "category", key: "category", width: widths.category, render: (v: string) => v ? <Tag>{v}</Tag> : "-" },
    { title: makeHeader("封装", "package_type", widths.package_type), dataIndex: "package_type", key: "package_type", width: widths.package_type },
    { title: makeHeader("规格", "specs", widths.specs), dataIndex: "specs", key: "specs", width: widths.specs, ellipsis: true },
    { title: makeHeader("单位", "unit", widths.unit), dataIndex: "unit", key: "unit", width: widths.unit },
    { title: makeHeader("品牌", "brand_name", widths.brand_name), dataIndex: "brand_name", key: "brand_name", width: widths.brand_name, render: (v: string | null) => v || "-" },
    {
      title: "操作", key: "actions", width: 160,
      render: (_: unknown, r: Product) => (
        <Space size="small">
          <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(r)}>编辑</Button>
          <Popconfirm title="确定删除?" onConfirm={() => handleDelete(r.id)}>
            <Button size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <style>{`
        .col-resize-handle:hover,
        .col-resize-handle:active {
          background: #1677ff !important;
        }
        body.col-resizing .col-resize-handle {
          background: #1677ff !important;
        }
      `}</style>

      <Card size="small" style={{ marginBottom: 16 }}>
        <Row gutter={[12, 12]} align="middle">
          <Col>
            <Input
              placeholder="自然语言搜索（如：0402 10uF MLCC）"
              prefix={<SearchOutlined />}
              value={q}
              onChange={(e) => setQ(e.target.value)}
              allowClear
              style={{ width: 320 }}
            />
          </Col>
          <Col flex="auto" />
          <Col>
            <Space>
              <Button icon={<ThunderboltOutlined />} onClick={() => setAiModalOpen(true)}>AI 解析</Button>
              <Button icon={<FileTextOutlined />} onClick={() => setBomModalOpen(true)}>BOM 导入</Button>
              <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>新建产品</Button>
            </Space>
          </Col>
        </Row>
      </Card>

      <Table
        ref={tableRef as any}
        rowKey="id"
        columns={columns as any}
        dataSource={data}
        loading={loading}
        tableLayout="fixed"
        onChange={(pagination) => { if (pagination.current) setPage(pagination.current); }}
        pagination={{
          current: page, total, pageSize: 20,
          showTotal: (t) => `共 ${t} 条`,
          onChange: (p) => setPage(p),
        }}
      />

      <Modal
        title={editing ? "编辑产品" : "新建产品"}
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={() => form.submit()}
        width={640}
      >
        <Form form={form} layout="vertical" onFinish={handleSave}>
          <Row gutter={12}>
            <Col span={12}><Form.Item name="name" label="名称" rules={[{ required: true }]}><Input /></Form.Item></Col>
            <Col span={12}><Form.Item name="sku" label="SKU"><Input /></Form.Item></Col>
          </Row>
          <Row gutter={12}>
            <Col span={8}><Form.Item name="category" label="分类"><Input /></Form.Item></Col>
            <Col span={8}><Form.Item name="package_type" label="封装"><Input /></Form.Item></Col>
            <Col span={8}><Form.Item name="unit" label="单位"><Input /></Form.Item></Col>
          </Row>
          <Form.Item name="specs" label="规格"><Input.TextArea rows={2} /></Form.Item>
          <Row gutter={12}>
            <Col span={12}>
              <Form.Item name="brand_id" label="品牌">
                <Select allowClear placeholder="选择品牌" options={brands.map((b) => ({ value: b.id, label: b.name_cn || b.name }))} />
              </Form.Item>
            </Col>
            <Col span={12}><Form.Item name="image_url" label="图片URL"><Input /></Form.Item></Col>
          </Row>
          <Form.Item name="notes" label="备注"><Input.TextArea rows={2} /></Form.Item>
        </Form>
      </Modal>

      <Modal
        title="AI 智能解析"
        open={aiModalOpen}
        onCancel={() => setAiModalOpen(false)}
        onOk={handleAiParse}
        confirmLoading={aiParsing}
        okText="解析并填充表单"
      >
        <p style={{ color: "#888", marginBottom: 8 }}>粘贴料号、型号、数据手册描述或供应商报价文本，AI 自动提取产品信息</p>
        <Input.TextArea
          rows={6}
          placeholder={"例如：\nSamsung CL05A105KP5NNNC\n0402 1uF ±10% 10V X5R MLCC\n原装正品，整盘4000PCS"}
          value={aiText}
          onChange={(e) => setAiText(e.target.value)}
        />
      </Modal>

      <Modal
        title="BOM 批量导入"
        open={bomModalOpen}
        onCancel={() => setBomModalOpen(false)}
        onOk={handleBomParse}
        confirmLoading={bomParsing}
        okText="解析并创建产品"
      >
        <p style={{ color: "#888", marginBottom: 8 }}>粘贴 BOM 清单，AI 逐行解析并自动创建产品。支持多行粘贴。</p>
        <Input.TextArea
          rows={10}
          placeholder={"例如：\n1 GRM155R61A105KE15 1uF 16V 0402 X5R 10% 100pcs\n2 CL05A105KP5NNNC 1uF 10V 0402 X5R 10% 200pcs"}
          value={bomText}
          onChange={(e) => setBomText(e.target.value)}
        />
      </Modal>
    </div>
  );
}
