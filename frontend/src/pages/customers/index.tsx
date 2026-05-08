import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Table, Button, Input, Space, Tag, Select, Row, Col, message, Popconfirm, Card, Modal, Upload, Tooltip, List, Typography, Empty, Popover, Checkbox } from "antd";
import { PlusOutlined, SearchOutlined, DownloadOutlined, DeleteOutlined, TagsOutlined, UploadOutlined, BarChartOutlined, ShoppingCartOutlined, PhoneOutlined, MailOutlined, MergeCellsOutlined, SafetyCertificateOutlined, SettingOutlined, SendOutlined } from "@ant-design/icons";
import type { ColumnsType, TablePaginationConfig } from "antd/es/table";
import type { SorterResult } from "antd/es/table/interface";
import { getCustomers, deleteCustomer, exportCustomers, batchDeleteCustomers, batchTagCustomers, getTags, downloadImportTemplate, importCustomers, getOverdueFollowUps, detectDuplicates, mergeCustomers, getAlertEvents, markAllAlertsRead, checkAlerts, searchSimilarCustomers } from "../../api";
import type { AlertEvent, Customer, DuplicatePair, OverdueFollowUp, SimilarCustomer, Tag as TagType } from "../../types";

const INDUSTRIES = ["汽车电子", "消费电子", "工业控制", "通信设备", "医疗设备", "安防监控", "其他"];
const LEVELS = ["A", "B", "C", "D"];
const REGIONS = ["华东", "华南", "华北", "华中", "西南", "西北", "东北", "海外"];
const SOURCES = ["展会", "转介绍", "线上推广", "陌生拜访", "公司资源"];

export default function CustomerList() {
  const [data, setData] = useState<Customer[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [q, setQ] = useState("");
  const [industry, setIndustry] = useState<string | undefined>();
  const [level, setLevel] = useState<string | undefined>();
  const [region, setRegion] = useState<string | undefined>();
  const [source, setSource] = useState<string | undefined>();
  const [creditLevel, setCreditLevel] = useState<string | undefined>();
  const [sortBy, setSortBy] = useState<string>("id");
  const [sortOrder, setSortOrder] = useState<string>("desc");
  const [selectedRowKeys, setSelectedRowKeys] = useState<number[]>([]);
  const [tagModalOpen, setTagModalOpen] = useState(false);
  const [tags, setTags] = useState<TagType[]>([]);
  const [batchTagIds, setBatchTagIds] = useState<number[]>([]);
  const [importing, setImporting] = useState(false);
  const [overdueList, setOverdueList] = useState<OverdueFollowUp[]>([]);
  const [duplicatePairs, setDuplicatePairs] = useState<DuplicatePair[]>([]);
  const [dupLoading, setDupLoading] = useState(false);
  const [dupModalOpen, setDupModalOpen] = useState(false);
  const [mergeModalOpen, setMergeModalOpen] = useState(false);
  const [merging, setMerging] = useState(false);
  const [mergeSource, setMergeSource] = useState<DuplicatePair | null>(null);
  const [alertCount, setAlertCount] = useState(0);
  const [alertChecking, setAlertChecking] = useState(false);
  const [semanticOpen, setSemanticOpen] = useState(false);
  const [semanticQ, setSemanticQ] = useState("");
  const [semanticResults, setSemanticResults] = useState<SimilarCustomer[]>([]);
  const [semanticLoading, setSemanticLoading] = useState(false);
  const allColKeys = ["code", "name", "industry", "level", "region", "tags", "owner", "contact_person", "source", "created_at", "actions"];
  const [visibleCols, setVisibleCols] = useState<string[]>([...allColKeys]);
  const navigate = useNavigate();
  const fileRef = useRef<HTMLInputElement>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout>>(undefined);

  const fetch = async (p = page, ps = pageSize, search = q) => {
    setLoading(true);
    try {
      const params: Record<string, unknown> = { page: p, page_size: ps, sort_by: sortBy, sort_order: sortOrder };
      if (search) params.q = search;
      if (industry) params.industry = industry;
      if (level) params.level = level;
      if (region) params.region = region;
      if (source) params.source = source;
      if (creditLevel) params.credit_level = creditLevel;
      const resp = await getCustomers(params);
      setData(resp.data.data.list);
      setTotal(resp.data.data.total);
    } catch {
      message.error("加载客户列表失败");
    } finally {
      setLoading(false);
    }
  };

  // Debounced search: auto-fetches 350ms after user stops typing
  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => { setPage(1); fetch(1, pageSize, q); }, 350);
    return () => { if (debounceRef.current) clearTimeout(debounceRef.current); };
  }, [q]);

  useEffect(() => { fetch(); }, [page, pageSize, industry, level, region, source, creditLevel, sortBy, sortOrder]);

  useEffect(() => {
    getTags().then((r) => setTags(r.data.data)).catch(() => {});
    getOverdueFollowUps().then((r) => setOverdueList(r.data.data?.items || [])).catch(() => {});
    getAlertEvents({ page: 1, page_size: 1, is_read: false }).then((r) => setAlertCount(r.data.data?.total || 0)).catch(() => {});
  }, []);


  const handleDelete = async (id: number) => {
    try { await deleteCustomer(id); message.success("已删除"); fetch(); } catch { message.error("删除失败"); }
  };

  const handleExport = async () => {
    try {
      const params: Record<string, unknown> = {};
      if (q) params.q = q;
      if (industry) params.industry = industry;
      if (level) params.level = level;
      const resp = await exportCustomers(params);
      const url = URL.createObjectURL(new Blob([resp.data]));
      const a = document.createElement("a");
      a.href = url; a.download = "customers.csv"; a.click();
      URL.revokeObjectURL(url);
      message.success("导出成功");
    } catch { message.error("导出失败"); }
  };

  const handleTemplate = async () => {
    try {
      const resp = await downloadImportTemplate();
      const url = URL.createObjectURL(new Blob([resp.data]));
      const a = document.createElement("a");
      a.href = url; a.download = "customer_template.csv"; a.click();
      URL.revokeObjectURL(url);
    } catch { message.error("下载模板失败"); }
  };

  const handleImport = async (file: File) => {
    setImporting(true);
    try {
      const resp = await importCustomers(file);
      const result = resp.data.data as { created: number; skipped: number };
      message.success(`导入成功: 新建 ${result.created} 条, 跳过 ${result.skipped} 条`);
      fetch();
    } catch { message.error("导入失败，请检查文件格式"); }
    finally { setImporting(false); }
    return false; // prevent default upload
  };

  const handleBatchDelete = async () => {
    try { await batchDeleteCustomers(selectedRowKeys); message.success(`已删除 ${selectedRowKeys.length} 条`); setSelectedRowKeys([]); fetch(); } catch { message.error("批量删除失败"); }
  };

  const handleBatchTag = async () => {
    if (batchTagIds.length === 0) return;
    try { await batchTagCustomers(selectedRowKeys, batchTagIds); message.success(`已为 ${selectedRowKeys.length} 个客户添加标签`); setSelectedRowKeys([]); setTagModalOpen(false); setBatchTagIds([]); fetch(); } catch { message.error("批量打标签失败"); }
  };

  const handleDetectDups = async () => {
    setDupLoading(true);
    try {
      const resp = await detectDuplicates(0.7);
      const pairs = (resp.data.data?.pairs || []) as DuplicatePair[];
      setDuplicatePairs(pairs);
      setDupModalOpen(true);
      if (pairs.length === 0) message.info("未发现疑似重复客户");
    } catch { message.error("检测失败"); }
    finally { setDupLoading(false); }
  };

  const openMergeModal = (pair: DuplicatePair) => {
    setMergeSource(pair);
    setMergeModalOpen(true);
  };

  const handleMerge = async () => {
    if (!mergeSource) return;
    setMerging(true);
    try {
      await mergeCustomers(mergeSource.customer_a.id, mergeSource.customer_b.id);
      message.success(`已合并至 ${mergeSource.customer_b.name}`);
      setMergeModalOpen(false);
      setMergeSource(null);
      setDupModalOpen(false);
      fetch();
    } catch { message.error("合并失败"); }
    finally { setMerging(false); }
  };

  const handleCheckAlerts = async () => {
    setAlertChecking(true);
    try {
      const resp = await checkAlerts();
      message.success(`预警检查完成，生成 ${resp.data.data.generated} 条`);
      getAlertEvents({ page: 1, page_size: 1, is_read: false }).then((r) => setAlertCount(r.data.data?.total || 0)).catch(() => {});
    } catch { message.error("预警检查失败"); }
    finally { setAlertChecking(false); }
  };

  const handleSemanticSearch = async () => {
    if (!semanticQ.trim()) return;
    setSemanticLoading(true);
    try {
      const resp = await searchSimilarCustomers(semanticQ);
      setSemanticResults((resp.data.data as SimilarCustomer[]) || []);
    } catch { message.error("语义搜索失败"); }
    finally { setSemanticLoading(false); }
  };

  const handleTableChange = (
    pag: TablePaginationConfig,
    _filters: unknown,
    sorter: SorterResult<Customer> | SorterResult<Customer>[],
  ) => {
    if (pag.current) setPage(pag.current);
    if (pag.pageSize) { setPageSize(pag.pageSize); setPage(1); }
    const s = Array.isArray(sorter) ? sorter[0] : sorter;
    if (s.field && typeof s.field === "string") {
      setSortBy(s.field);
      setSortOrder(s.order === "ascend" ? "asc" : s.order === "descend" ? "desc" : "desc");
    }
  };

  const columns: ColumnsType<Customer> = [
    { title: "客户编码", dataIndex: "code", key: "code", width: 120, sorter: true, sortOrder: sortBy === "code" ? (sortOrder === "asc" ? "ascend" : "descend") : null },
    { title: "客户名称", dataIndex: "name", key: "name", width: 200, sorter: true, sortOrder: sortBy === "name" ? (sortOrder === "asc" ? "ascend" : "descend") : null, render: (text: string, r: Customer) => (<a onClick={() => navigate(`/customers/${r.id}`)}>{text}</a>) },
    { title: "行业", dataIndex: "industry", key: "industry", width: 100, sorter: true, sortOrder: sortBy === "industry" ? (sortOrder === "asc" ? "ascend" : "descend") : null },
    { title: "等级", dataIndex: "level", key: "level", width: 80, sorter: true, sortOrder: sortBy === "level" ? (sortOrder === "asc" ? "ascend" : "descend") : null, render: (v: string) => <Tag color={v === "A" ? "red" : v === "B" ? "orange" : "default"}>{v}</Tag> },
    { title: "区域", dataIndex: "region", key: "region", width: 100, sorter: true, sortOrder: sortBy === "region" ? (sortOrder === "asc" ? "ascend" : "descend") : null },
    { title: "标签", dataIndex: "tags", key: "tags", width: 160, render: (tags: TagType[]) => tags?.map((t) => <Tag key={t.id} color={t.color || "blue"}>{t.name}</Tag>) },
    { title: "负责人", dataIndex: "owner", key: "owner", width: 80 },
    { title: "联系人", dataIndex: "contact_person", key: "contact_person", width: 100 },
    { title: "来源", dataIndex: "source", key: "source", width: 80, sorter: true, sortOrder: sortBy === "source" ? (sortOrder === "asc" ? "ascend" : "descend") : null },
    { title: "创建时间", dataIndex: "created_at", key: "created_at", width: 100, sorter: true, sortOrder: sortBy === "created_at" ? (sortOrder === "asc" ? "ascend" : "descend") : null, render: (v: string) => v?.slice(0, 10) },
    {
      title: "操作", key: "actions", width: 220, render: (_: unknown, r: Customer) => (
        <Space size={4}>
          <Button size="small" onClick={() => navigate(`/customers/${r.id}`)}>详情</Button>
          <Tooltip title="创建销售订单">
            <Button size="small" icon={<ShoppingCartOutlined />} onClick={() => navigate(`/sales/orders/new?customer_id=${r.id}`)} />
          </Tooltip>
          <Tooltip title="新增跟进">
            <Button size="small" icon={<PhoneOutlined />} onClick={() => navigate(`/customers/${r.id}?tab=followups`)} />
          </Tooltip>
          <Popconfirm title="确定删除?" onConfirm={() => handleDelete(r.id)}>
            <Button size="small" danger>删除</Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <Card size="small" style={{ marginBottom: 16 }}>
        <Row gutter={[12, 12]} align="middle">
          <Col>
            <Input
              placeholder="搜索客户名称/编码"
              prefix={<SearchOutlined />}
              value={q}
              onChange={(e) => setQ(e.target.value)}
              allowClear
              style={{ width: 240 }}
            />
          </Col>
          <Col><Select allowClear placeholder="行业" style={{ width: 110 }} value={industry} onChange={(v) => { setIndustry(v); setPage(1); }} options={INDUSTRIES.map((v) => ({ value: v, label: v }))} /></Col>
          <Col><Select allowClear placeholder="等级" style={{ width: 80 }} value={level} onChange={(v) => { setLevel(v); setPage(1); }} options={LEVELS.map((v) => ({ value: v, label: v }))} /></Col>
          <Col><Select allowClear placeholder="区域" style={{ width: 100 }} value={region} onChange={(v) => { setRegion(v); setPage(1); }} options={REGIONS.map((v) => ({ value: v, label: v }))} /></Col>
          <Col><Select allowClear placeholder="来源" style={{ width: 100 }} value={source} onChange={(v) => { setSource(v); setPage(1); }} options={SOURCES.map((v) => ({ value: v, label: v }))} /></Col>
          <Col><Select allowClear placeholder="信用等级" style={{ width: 100 }} value={creditLevel} onChange={(v) => { setCreditLevel(v); setPage(1); }} options={LEVELS.map((v) => ({ value: v, label: v }))} /></Col>
          <Col flex="auto" />
          <Col>
            <Space>
              {selectedRowKeys.length > 0 && (
                <>
                  <Popconfirm title={`确定删除 ${selectedRowKeys.length} 个客户?`} onConfirm={handleBatchDelete}>
                    <Button danger icon={<DeleteOutlined />}>批量删除</Button>
                  </Popconfirm>
                  <Button icon={<TagsOutlined />} onClick={() => setTagModalOpen(true)}>批量打标签</Button>
                </>
              )}
              <Upload accept=".csv" showUploadList={false} beforeUpload={handleImport} disabled={importing}>
                <Button icon={<UploadOutlined />} loading={importing}>导入</Button>
              </Upload>
              <Button onClick={handleTemplate}>模板</Button>
              <Button icon={<DownloadOutlined />} onClick={handleExport}>导出</Button>
              <Button icon={<BarChartOutlined />} onClick={() => navigate("/customers/stats")}>统计</Button>
              <Popover
                content={
                  <Checkbox.Group
                    options={allColKeys.map((k) => {
                      const labelMap: Record<string, string> = { code: "编码", name: "名称", industry: "行业", level: "等级", region: "区域", tags: "标签", owner: "负责人", contact_person: "联系人", source: "来源", created_at: "创建时间", actions: "操作" };
                      return { label: labelMap[k] || k, value: k };
                    })}
                    value={visibleCols}
                    onChange={(vals) => setVisibleCols(vals as string[])}
                  />
                }
                title="显示列"
                trigger="click"
              >
                <Button icon={<SettingOutlined />}>列</Button>
              </Popover>
              <Button icon={<SafetyCertificateOutlined />} loading={dupLoading} onClick={handleDetectDups}>查重</Button>
              <Button icon={<SendOutlined />} onClick={() => setSemanticOpen(true)}>语义搜索</Button>
              <Button danger={alertCount > 0} loading={alertChecking} onClick={handleCheckAlerts}>
                {alertCount > 0 ? `预警(${alertCount})` : "预警"}
              </Button>
              <Button type="primary" icon={<PlusOutlined />} onClick={() => navigate("/customers/new")}>新建客户</Button>
            </Space>
          </Col>
        </Row>
      </Card>

      {overdueList.length > 0 && (
        <Card size="small" style={{ marginBottom: 16, borderColor: "#ff4d4f" }}
          title={<span style={{ color: "#ff4d4f" }}>跟进提醒 ({overdueList.length})</span>}
        >
          <div style={{ maxHeight: 160, overflow: "auto" }}>
            {overdueList.slice(0, 10).map((o) => (
              <Tag key={o.id} color="error" style={{ marginBottom: 4, cursor: "pointer" }}
                onClick={() => navigate(`/customers/${o.customer_id}`)}
              >
                {o.customer_name}: {o.method} — 逾期 {o.overdue_days} 天 {o.owner ? `(@${o.owner})` : ""}
              </Tag>
            ))}
            {overdueList.length > 10 && <div style={{ color: "#888", fontSize: 12 }}>还有 {overdueList.length - 10} 条...</div>}
          </div>
        </Card>
      )}

      <Table
        rowKey="id"
        columns={columns.filter((c) => visibleCols.includes(String(c.key)))}
        dataSource={data}
        loading={loading}
        onChange={handleTableChange}
        rowSelection={{
          selectedRowKeys,
          onChange: (keys) => setSelectedRowKeys(keys as number[]),
        }}
        pagination={{
          current: page,
          total,
          pageSize,
          pageSizeOptions: ["10", "20", "50", "100"],
          showSizeChanger: true,
          showTotal: (t) => `共 ${t} 条`,
          onChange: (p, ps) => { setPage(p); setPageSize(ps); },
        }}
      />

      <Modal title="选择标签" open={tagModalOpen} onCancel={() => setTagModalOpen(false)} onOk={handleBatchTag}>
        <Select mode="multiple" style={{ width: "100%" }} placeholder="选择要添加的标签" value={batchTagIds} onChange={(v) => setBatchTagIds(v)} options={tags.map((t) => ({ value: t.id, label: t.name }))} />
      </Modal>

      <Modal title="疑似重复客户" open={dupModalOpen} onCancel={() => setDupModalOpen(false)} footer={null} width={700}>
        {duplicatePairs.length === 0 ? (
          <Empty description="未发现疑似重复客户" />
        ) : (
          <List
            dataSource={duplicatePairs}
            renderItem={(pair) => (
              <List.Item
                actions={[
                  <Button key="merge" icon={<MergeCellsOutlined />} onClick={() => openMergeModal(pair)}>合并</Button>,
                ]}
              >
                <List.Item.Meta
                  title={
                    <Space>
                      <Typography.Text>{pair.customer_a.name}</Typography.Text>
                      <Tag color="orange">相似 {(pair.similarity * 100).toFixed(0)}%</Tag>
                      <Typography.Text>{pair.customer_b.name}</Typography.Text>
                    </Space>
                  }
                  description={
                    <Space size={16}>
                      <span>📞 {pair.customer_a.phone || "-"}</span>
                      <span>📞 {pair.customer_b.phone || "-"}</span>
                      <span>👤 {pair.customer_a.owner || "-"}</span>
                      <span>👤 {pair.customer_b.owner || "-"}</span>
                    </Space>
                  }
                />
              </List.Item>
            )}
          />
        )}
      </Modal>

      <Modal
        title="语义搜索"
        open={semanticOpen}
        onCancel={() => setSemanticOpen(false)}
        footer={null}
        width={600}
      >
        <Space.Compact style={{ width: "100%", marginBottom: 16 }}>
          <Input
            placeholder="输入自然语言描述，例如：华东地区做汽车电子的A级客户"
            value={semanticQ}
            onChange={(e) => setSemanticQ(e.target.value)}
            onPressEnter={handleSemanticSearch}
          />
          <Button type="primary" loading={semanticLoading} onClick={handleSemanticSearch}>搜索</Button>
        </Space.Compact>
        <Table
          dataSource={semanticResults}
          rowKey="id"
          size="small"
          pagination={false}
          locale={{ emptyText: semanticQ && !semanticLoading ? "未找到匹配客户" : "输入关键词后搜索" }}
          columns={[
            { title: "客户名称", dataIndex: "name", key: "name", render: (name: string, r: SimilarCustomer) => <a onClick={() => { setSemanticOpen(false); navigate(`/customers/${r.id}`); }}>{name}</a> },
            { title: "行业", dataIndex: "industry", key: "industry", render: (v: string) => <Tag>{v || "-"}</Tag> },
            { title: "区域", dataIndex: "region", key: "region" },
            { title: "相似度", dataIndex: "similarity", key: "similarity", render: (v: number) => `${(v * 100).toFixed(1)}%` },
          ]}
        />
      </Modal>

      <Modal
        title="合并客户"
        open={mergeModalOpen}
        onCancel={() => { setMergeModalOpen(false); setMergeSource(null); }}
        onOk={handleMerge}
        confirmLoading={merging}
        okText="确认合并"
        okButtonProps={{ danger: true }}
      >
        {mergeSource && (
          <div>
            <p>确认将以下客户合并？</p>
            <Card size="small" style={{ marginBottom: 12, backgroundColor: "#fff2f0" }}>
              <Typography.Text strong delete>源客户: {mergeSource.customer_a.name}</Typography.Text>
              <div style={{ fontSize: 12, color: "#888" }}>电话: {mergeSource.customer_a.phone || "无"} | 负责人: {mergeSource.customer_a.owner || "无"}</div>
            </Card>
            <Card size="small" style={{ backgroundColor: "#f6ffed" }}>
              <Typography.Text strong>目标客户: {mergeSource.customer_b.name}</Typography.Text>
              <div style={{ fontSize: 12, color: "#888" }}>电话: {mergeSource.customer_b.phone || "无"} | 负责人: {mergeSource.customer_b.owner || "无"}</div>
            </Card>
            <p style={{ marginTop: 12, color: "#ff4d4f" }}>
              合并后，源客户的所有联系人、跟进记录、标签、附件和订单将转移到目标客户，源客户将被删除。
            </p>
          </div>
        )}
      </Modal>
    </div>
  );
}
