import { useEffect, useRef, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { Table, Button, Input, Space, Tag, message, Modal, Form, Select, Popconfirm, Card, Row, Col, Popover, Checkbox, Tooltip } from "antd";
import { PlusOutlined, SearchOutlined, ThunderboltOutlined, FileTextOutlined, EditOutlined, DeleteOutlined, SettingOutlined, DownloadOutlined, UploadOutlined } from "@ant-design/icons";
import type { ColumnsType, TablePaginationConfig } from "antd/es/table";
import type { SorterResult } from "antd/es/table/interface";
import { getProducts, createProduct, updateProduct, deleteProduct, getBrands, aiParseProduct, aiParseBom, batchDeleteProducts, batchUpdateProducts, importProducts, aiSearchProducts } from "../../api";
import type { Product, Brand } from "../../types";

const CATEGORIES = ["MLCC", "IC", "电阻", "电容", "连接器", "晶体管", "传感器", "电源管理", "存储", "其他"];
const STOCK_OPTIONS = [
  { value: "", label: "全部" },
  { value: "in_stock", label: "在库" },
  { value: "out_of_stock", label: "缺货" },
  { value: "low_stock", label: "低库存" },
];
const SORT_OPTIONS = [
  { value: "created_at_desc", label: "最新优先" },
  { value: "created_at_asc", label: "最旧优先" },
  { value: "name_asc", label: "名称升序" },
  { value: "name_desc", label: "名称降序" },
];

const COL_LABEL_MAP: Record<string, string> = {
  sku: "SKU", name: "产品名称", category: "分类", package_type: "封装",
  specs: "规格", unit: "单位", brand_name: "品牌",
  quantity: "库存", available: "可用", locked: "锁定", safety_stock: "安全库存",
  unit_price: "单价", actions: "操作",
};

export default function ProductList() {
  const [data, setData] = useState<Product[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [q, setQ] = useState("");
  const [aiSearchMode, setAiSearchMode] = useState(false);
  const [aiSearchResults, setAiSearchResults] = useState<Record<string, unknown>[] | null>(null);
  const [aiSearching, setAiSearching] = useState(false);
  const [category, setCategory] = useState<string | undefined>();
  const [brandId, setBrandId] = useState<number | undefined>();
  const [stockStatus, setStockStatus] = useState<string | undefined>();
  const [sort, setSort] = useState<string>("created_at_desc");
  const [sortBy, setSortBy] = useState<string>("created_at");
  const [sortOrder, setSortOrder] = useState<string>("desc");
  const [selectedRowKeys, setSelectedRowKeys] = useState<number[]>([]);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<Product | null>(null);
  const [brands, setBrands] = useState<Brand[]>([]);
  const [aiModalOpen, setAiModalOpen] = useState(false);
  const [aiText, setAiText] = useState("");
  const [aiParsing, setAiParsing] = useState(false);
  const [bomModalOpen, setBomModalOpen] = useState(false);
  const [bomText, setBomText] = useState("");
  const [bomParsing, setBomParsing] = useState(false);
  const [importModalOpen, setImportModalOpen] = useState(false);
  const [importFile, setImportFile] = useState<File | null>(null);
  const [importing, setImporting] = useState(false);
  const [batchEditModalOpen, setBatchEditModalOpen] = useState(false);
  const [batchEditForm] = Form.useForm();
  const [batchEditing, setBatchEditing] = useState(false);
  const [compareOpen, setCompareOpen] = useState(false);
  const [form] = Form.useForm();
  const debounceRef = useRef<ReturnType<typeof setTimeout>>(undefined);
  const navigate = useNavigate();
  const allColKeys = ["sku", "name", "category", "package_type", "specs", "unit", "brand_name", "quantity", "available", "locked", "safety_stock", "unit_price", "actions"];
  const [visibleCols, setVisibleCols] = useState<string[]>([...allColKeys]);

  // Direct DOM column resize
  const resizing = useRef<{ th: HTMLTableCellElement; startX: number; startW: number } | null>(null);
  const onHeaderMouseDown = useCallback((e: React.MouseEvent<HTMLTableCellElement>) => {
    const th = e.currentTarget as HTMLTableCellElement;
    e.preventDefault(); e.stopPropagation();
    resizing.current = { th, startX: e.clientX, startW: th.offsetWidth };
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
    document.body.classList.add("col-resizing");
  }, []);

  useEffect(() => {
    const onMouseMove = (e: MouseEvent) => {
      if (!resizing.current) return;
      const delta = e.clientX - resizing.current.startX;
      const next = Math.max(40, resizing.current.startW + delta);
      resizing.current.th.style.width = `${next}px`;
      resizing.current.th.style.minWidth = `${next}px`;
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
    return () => { document.removeEventListener("mousemove", onMouseMove); document.removeEventListener("mouseup", onMouseUp); };
  }, []);

  const fetch = async (p = page, search = q) => {
    if (aiSearchMode) return; // AI mode bypasses normal fetch
    setLoading(true);
    try {
      const params: Record<string, unknown> = { page: p, page_size: 20, sort };
      if (search) params.q = search;
      if (category) params.category = category;
      if (brandId) params.brand_id = brandId;
      if (stockStatus) params.stock_status = stockStatus;
      const resp = await getProducts(params);
      const list = (resp.data.data.list || []) as any[];
      setData(list);
      setTotal(resp.data.data.total || 0);
    } catch { message.error("加载产品列表失败"); }
    finally { setLoading(false); }
  };

  const handleAiSearch = useCallback(async (text: string) => {
    if (!text.trim()) { setAiSearchResults(null); return; }
    setAiSearching(true);
    try {
      const r = await aiSearchProducts(text, 20);
      if (r.data.code === 0) {
        setAiSearchResults(r.data.data as Record<string, unknown>[]);
      } else {
        message.error(r.data.msg || "搜索失败");
      }
    } catch { message.error("AI 搜索失败"); }
    finally { setAiSearching(false); }
  }, []);

  const loadBrands = async () => {
    try {
      const r = await getBrands();
      setBrands((r.data.data || []) as Brand[]);
    } catch { /* silent */ }
  };

  useEffect(() => { loadBrands(); }, []);
  useEffect(() => { fetch(); }, [page, sort]);

  // Debounced search
  useEffect(() => {
    if (aiSearchMode) return;
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => { setPage(1); fetch(1, q); }, 350);
    return () => { if (debounceRef.current) clearTimeout(debounceRef.current); };
  }, [q, aiSearchMode]);

  // AI search trigger
  useEffect(() => {
    if (aiSearchMode && q.trim()) {
      const t = setTimeout(() => handleAiSearch(q), 500);
      return () => clearTimeout(t);
    } else {
      setAiSearchResults(null);
    }
  }, [q, aiSearchMode, handleAiSearch]);

  // Filter triggers
  useEffect(() => { setPage(1); fetch(1); }, [category, brandId, stockStatus]);

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

  const handleBatchDelete = async () => {
    try {
      await batchDeleteProducts(selectedRowKeys);
      message.success(`已删除 ${selectedRowKeys.length} 个产品`);
      setSelectedRowKeys([]);
      fetch();
    } catch { message.error("批量删除失败"); }
  };

  const handleBatchUpdate = async (values: Record<string, unknown>) => {
    if (!selectedRowKeys.length) { message.warning("未选中产品"); return; }
    setBatchEditing(true);
    try {
      const fields = Object.fromEntries(Object.entries(values).filter(([, v]) => v !== undefined && v !== null && v !== ""));
      await batchUpdateProducts(selectedRowKeys, fields);
      message.success(`批量更新成功：${selectedRowKeys.length} 个产品`);
      setBatchEditModalOpen(false);
      setSelectedRowKeys([]);
      fetch();
    } catch { message.error("批量更新失败"); }
    finally { setBatchEditing(false); }
  };

  const handleExport = () => {
    if (data.length === 0) { message.warning("无数据可导出"); return; }
    const headers = ["SKU", "产品名称", "分类", "封装", "规格", "单位", "品牌", "库存", "可用", "锁定", "安全库存", "单价"];
    const rows = data.map((p) => [
      p.sku || "", p.name || "", p.category || "", p.package_type || "",
      p.specs || "", p.unit || "", p.brand_name || "",
      p.quantity ?? 0, p.available ?? 0, p.locked_quantity ?? 0,
      p.safety_stock ?? "", p.unit_price != null ? `¥${p.unit_price.toFixed(2)}` : "",
    ]);
    const csv = [headers, ...rows].map((r) => r.map((c) => `"${c}"`).join(",")).join("\n");
    const blob = new Blob(["﻿" + csv], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = "products.csv"; a.click();
    URL.revokeObjectURL(url);
    message.success("导出成功");
  };

  const handleAiParse = async () => {
    if (!aiText.trim()) return;
    setAiParsing(true);
    try {
      const resp = await aiParseProduct(aiText.trim());
      const parsed = resp.data.data as Record<string, unknown>;
      const specsStr = parsed.specs && typeof parsed.specs === "object"
        ? JSON.stringify(parsed.specs) : String(parsed.specs || "");
      let brandIdVal: number | undefined;
      const brandName = String(parsed.brand_name || "").toLowerCase();
      if (brandName) {
        const match = brands.find((b) =>
          b.name.toLowerCase().includes(brandName) || (b.name_cn || "").toLowerCase().includes(brandName)
        );
        if (match) brandIdVal = match.id;
      }
      form.setFieldsValue({
        name: parsed.name, sku: parsed.sku || undefined,
        category: parsed.category || undefined, package_type: parsed.package_type || undefined,
        specs: specsStr, unit: parsed.unit || undefined, brand_id: brandIdVal,
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

  const handleImport = async () => {
    if (!importFile) { message.warning("请先选择文件"); return; }
    setImporting(true);
    try {
      const resp = await importProducts(importFile);
      if (resp.data.code === 0) {
        const d = resp.data.data as { created: number; errors: string[] };
        message.success(`导入成功：新增 ${d.created} 个产品`);
        if (d.errors?.length) {
          message.warning(`部分行失败：${d.errors.slice(0, 3).join("；")}`);
        }
        setImportModalOpen(false);
        setImportFile(null);
        fetch(1);
      } else {
        message.error(resp.data.msg || "导入失败");
      }
    } catch { message.error("导入失败，请检查文件格式"); }
    finally { setImporting(false); }
  };

  const handleTableChange = (
    _pagination: TablePaginationConfig,
    _filters: unknown,
    sorter: SorterResult<Product> | SorterResult<Product>[],
  ) => {
    const s = Array.isArray(sorter) ? sorter[0] : sorter;
    if (s.field) {
      const fieldMap: Record<string, string> = { name: "name_asc", sku: "sku_asc", category: "category_asc", created_at: "created_at_asc" };
      const field = String(s.field);
      if (s.order === "ascend") {
        setSort(fieldMap[field] || "name_asc");
      } else if (s.order === "descend") {
        setSort(fieldMap[field]?.replace("_asc", "_desc") || "name_desc");
      }
    }
  };

  const columns: ColumnsType<Product> = [
    { title: "SKU", dataIndex: "sku", key: "sku", width: 120, onCell: () => ({ onMouseDown: onHeaderMouseDown }) },
    { title: "产品名称", dataIndex: "name", key: "name", width: 200, sorter: true, onCell: () => ({ onMouseDown: onHeaderMouseDown }), render: (text: string, r: Product) => <a onClick={() => navigate(`/products/${r.id}`)}>{text}</a> },
    { title: "分类", dataIndex: "category", key: "category", width: 80, onCell: () => ({ onMouseDown: onHeaderMouseDown }), render: (v: string) => v ? <Tag>{v}</Tag> : "-" },
    { title: "封装", dataIndex: "package_type", key: "package_type", width: 90, onCell: () => ({ onMouseDown: onHeaderMouseDown }) },
    { title: "规格", dataIndex: "specs", key: "specs", width: 180, onCell: () => ({ onMouseDown: onHeaderMouseDown }), ellipsis: true },
    { title: "单位", dataIndex: "unit", key: "unit", width: 60, onCell: () => ({ onMouseDown: onHeaderMouseDown }) },
    { title: "品牌", dataIndex: "brand_name", key: "brand_name", width: 100, onCell: () => ({ onMouseDown: onHeaderMouseDown }), render: (v: string | null) => v || "-" },
    { title: "库存", dataIndex: "quantity", key: "quantity", width: 80, onCell: () => ({ onMouseDown: onHeaderMouseDown }), render: (v: number | null) => v != null ? v : 0 },
    { title: "可用", dataIndex: "available", key: "available", width: 80, onCell: () => ({ onMouseDown: onHeaderMouseDown }), render: (v: number | null) => v != null ? v : 0 },
    { title: "锁定", dataIndex: "locked_quantity", key: "locked", width: 70, onCell: () => ({ onMouseDown: onHeaderMouseDown }), render: (v: number | null) => v != null ? v : 0 },
    { title: "安全库存", dataIndex: "safety_stock", key: "safety_stock", width: 80, onCell: () => ({ onMouseDown: onHeaderMouseDown }), render: (v: number | null) => v != null ? v : "-" },
    { title: "单价", dataIndex: "unit_price", key: "unit_price", width: 90, onCell: () => ({ onMouseDown: onHeaderMouseDown }), render: (v: number | null) => v != null ? `¥${v.toFixed(2)}` : "-" },
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
        .ant-table-cell { position: relative; cursor: col-resize; user-select: none; }
        .ant-table-cell::after { content: ''; position: absolute; right: 0; top: 15%; height: 70%; width: 3px; background: transparent; border-radius: 2px; transition: background 0.15s; }
        .ant-table-cell:hover::after, .ant-table-cell.resizing::after { background: #1677ff; }
        body.col-resizing * { cursor: col-resize !important; }
      `}</style>

      <Card size="small" style={{ marginBottom: 16 }}>
        <Row gutter={[12, 12]} align="middle">
          <Col>
            <Input
              placeholder={aiSearchMode ? "AI 语义搜索（如：高频放大器 贴片）" : "自然语言搜索（如：0402 10uF MLCC）"}
              prefix={<SearchOutlined />}
              value={q}
              onChange={(e) => setQ(e.target.value)}
              allowClear
              style={{ width: aiSearchMode ? 340 : 300 }}
              suffix={
                <Tooltip title={aiSearchMode ? "切换普通搜索" : "切换 AI 语义搜索"}>
                  <Button
                    size="small"
                    type={aiSearchMode ? "primary" : "default"}
                    icon={<ThunderboltOutlined />}
                    onClick={() => { setAiSearchMode(!aiSearchMode); if (aiSearchMode) { setAiSearchResults(null); } else { setQ(""); setPage(1); fetch(1, ""); } }}
                    style={{ marginLeft: 4 }}
                  />
                </Tooltip>
              }
            />
          </Col>
          <Col>
            <Select allowClear placeholder="分类" style={{ width: 100 }}
              value={category} onChange={(v) => { setCategory(v); setPage(1); }}
              options={CATEGORIES.map((v) => ({ value: v, label: v }))} />
          </Col>
          <Col>
            <Select allowClear placeholder="品牌" style={{ width: 130 }}
              value={brandId} onChange={(v) => { setBrandId(v); setPage(1); }}
              options={brands.map((b) => ({ value: b.id, label: b.name_cn || b.name }))} />
          </Col>
          <Col>
            <Select placeholder="库存状态" style={{ width: 110 }}
              value={stockStatus} onChange={(v) => { setStockStatus(v); setPage(1); }}
              options={STOCK_OPTIONS} />
          </Col>
          <Col>
            <Select value={sort} onChange={(v) => { setSort(v); setPage(1); }}
              options={SORT_OPTIONS} style={{ width: 110 }} />
          </Col>
          <Col flex="auto" />
          <Col>
            <Space>
              {selectedRowKeys.length > 0 && (
                <>
                  <Popconfirm title={`确定删除 ${selectedRowKeys.length} 个产品?`} onConfirm={handleBatchDelete}>
                    <Button danger icon={<DeleteOutlined />}>批量删除</Button>
                  </Popconfirm>
                  <Button icon={<EditOutlined />} onClick={() => { batchEditForm.resetFields(); setBatchEditModalOpen(true); }}>批量编辑</Button>
                </>
              )}
              <Button icon={<UploadOutlined />} onClick={() => setImportModalOpen(true)}>导入</Button>
              <Button icon={<DownloadOutlined />} onClick={handleExport}>导出</Button>
              <Popover
                content={
                  <Checkbox.Group
                    options={allColKeys.map((k) => ({ label: COL_LABEL_MAP[k] || k, value: k }))}
                    value={visibleCols}
                    onChange={(vals) => setVisibleCols(vals as string[])}
                  />
                }
                title="显示列" trigger="click"
              >
                <Button icon={<SettingOutlined />}>列</Button>
              </Popover>
              <Button icon={<ThunderboltOutlined />} onClick={() => setAiModalOpen(true)}>AI 解析</Button>
              <Button icon={<FileTextOutlined />} onClick={() => setBomModalOpen(true)}>BOM 导入</Button>
              <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>新建产品</Button>
            </Space>
          </Col>
        </Row>
      </Card>

      <Table
        rowKey="id"
        columns={columns.filter((c) => visibleCols.includes(String(c.key)))}
        dataSource={aiSearchMode ? (aiSearchResults ?? []) as unknown as Product[] : data}
        loading={aiSearchMode ? aiSearching : loading}
        tableLayout="fixed"
        onChange={handleTableChange}
        rowSelection={{
          selectedRowKeys,
          onChange: (keys) => setSelectedRowKeys(keys as number[]),
      }}
      pagination={false}
    />

    {/* Compare Panel */}
    {selectedRowKeys.length >= 2 && (
      <Card
        title={`产品对比（${selectedRowKeys.length} 个）`}
        extra={<Button size="small" onClick={() => setSelectedRowKeys([])}>清除选择</Button>}
        style={{ marginTop: 16 }}
        size="small"
      >
        <Table
          rowKey="id"
          size="small"
          pagination={false}
          dataSource={data.filter((p) => selectedRowKeys.includes(p.id)) as Product[]}
          columns={[
            { title: "SKU", dataIndex: "sku", width: 100 },
            { title: "产品名称", dataIndex: "name", width: 160 },
            { title: "分类", dataIndex: "category", width: 80 },
            { title: "封装", dataIndex: "package_type", width: 80 },
            { title: "规格", dataIndex: "specs", ellipsis: true, width: 150 },
            { title: "品牌", dataIndex: "brand_name", width: 100 },
            { title: "库存", dataIndex: "quantity", width: 60 },
            { title: "可用", dataIndex: "available", width: 60 },
            { title: "安全库存", dataIndex: "safety_stock", width: 80 },
            { title: "单价", dataIndex: "unit_price", width: 80, render: (v: number | null) => v != null ? `¥${v.toFixed(2)}` : "-" },
          ]}
          scroll={{ x: true }}
          style={{ overflowX: "auto" }}
        />
      </Card>
    )}

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

      <Modal
        title="批量导入产品"
        open={importModalOpen}
        onCancel={() => { setImportModalOpen(false); setImportFile(null); }}
        onOk={handleImport}
        confirmLoading={importing}
        okText="导入"
        width={480}
      >
        <p style={{ color: "#888", marginBottom: 16 }}>
          支持 CSV / XLSX 文件，列：<code>name, sku, category, brand, package_type, specs, unit, notes</code>
        </p>
        <input
          type="file"
          accept=".csv,.xlsx"
          onChange={(e) => setImportFile(e.target.files?.[0] || null)}
          style={{ marginBottom: 8 }}
        />
        {importFile && <p style={{ color: "#555" }}>已选：{importFile.name}</p>}
        <a
          href="/products_template.csv"
          download
          style={{ fontSize: 12, color: "#1677ff" }}
          onClick={(e) => {
            e.preventDefault();
            // Generate template CSV content
            const headers = ["name", "sku", "category", "brand", "package_type", "specs", "unit", "notes"];
            const sample = ["8658B传感器", "8658B", "传感器", "QST", "BGA", "原装正品", "pcs", "导入备注"];
            const csv = [headers, sample].map((r) => r.map((c) => `"${c}"`).join(",")).join("\n");
            const blob = new Blob(["\uFEFF" + csv], { type: "text/csv;charset=utf-8" });
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url; a.download = "products_template.csv"; a.click();
            URL.revokeObjectURL(url);
          }}
        >
          下载模板文件
        </a>
      </Modal>

      <Modal
        title={`批量编辑 ${selectedRowKeys.length > 0 ? `（已选 ${selectedRowKeys.length} 个）` : ""}`}
        open={batchEditModalOpen}
        onCancel={() => setBatchEditModalOpen(false)}
        onOk={() => batchEditForm.submit()}
        confirmLoading={batchEditing}
        okText="保存更新"
        width={500}
      >
        <p style={{ color: "#888", marginBottom: 16 }}>留空字段将保持不变，已选中 <strong>{selectedRowKeys.length}</strong> 个产品</p>
        <Form form={batchEditForm} layout="vertical" onFinish={handleBatchUpdate}>
          <Row gutter={12}>
            <Col span={12}>
              <Form.Item name="brand_id" label="品牌">
                <Select allowClear placeholder="保持不变" options={brands.map((b) => ({ value: b.id, label: b.name_cn || b.name }))} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="category" label="分类">
                <Input placeholder="保持不变" />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={12}>
            <Col span={12}>
              <Form.Item name="package_type" label="封装">
                <Input placeholder="保持不变" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="unit" label="单位">
                <Input placeholder="保持不变" />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={12}>
            <Col span={12}>
              <Form.Item name="category" label="分类">
                <Input placeholder="保持不变" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="brand_id" label="品牌">
                <Select allowClear placeholder="保持不变" options={brands.map((b) => ({ value: b.id, label: b.name_cn || b.name }))} />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item name="specs" label="规格">
            <Input.TextArea rows={2} placeholder="保持不变" />
          </Form.Item>
          <Form.Item name="notes" label="备注">
            <Input.TextArea rows={2} placeholder="保持不变" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}