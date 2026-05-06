import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Table, Button, Input, Space, Tag, Select, Row, Col, message, Popconfirm, Card, Modal, Form } from "antd";
import { PlusOutlined, SearchOutlined, DownloadOutlined, DeleteOutlined, TagsOutlined } from "@ant-design/icons";
import { getCustomers, deleteCustomer, exportCustomers, batchDeleteCustomers, batchTagCustomers, getTags } from "../../api";
import type { Customer, Tag as TagType } from "../../types";

const INDUSTRIES = ["汽车电子", "消费电子", "工业控制", "通信设备", "医疗设备", "安防监控", "其他"];
const LEVELS = ["A", "B", "C", "D"];
const REGIONS = ["华东", "华南", "华北", "华中", "西南", "西北", "东北", "海外"];
const SOURCES = ["展会", "转介绍", "线上推广", "陌生拜访", "公司资源"];

export default function CustomerList() {
  const [data, setData] = useState<Customer[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [q, setQ] = useState("");
  const [industry, setIndustry] = useState<string | undefined>();
  const [level, setLevel] = useState<string | undefined>();
  const [region, setRegion] = useState<string | undefined>();
  const [source, setSource] = useState<string | undefined>();
  const [creditLevel, setCreditLevel] = useState<string | undefined>();
  const [selectedRowKeys, setSelectedRowKeys] = useState<number[]>([]);
  const [tagModalOpen, setTagModalOpen] = useState(false);
  const [tags, setTags] = useState<TagType[]>([]);
  const [batchTagIds, setBatchTagIds] = useState<number[]>([]);
  const navigate = useNavigate();

  const fetch = async (p = page, search = q) => {
    setLoading(true);
    try {
      const params: Record<string, unknown> = { page: p, page_size: 20 };
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

  useEffect(() => { fetch(); }, [page, industry, level, region, source, creditLevel]);

  useEffect(() => {
    getTags().then((r) => setTags(r.data.data)).catch(() => {});
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

  const handleBatchDelete = async () => {
    try {
      await batchDeleteCustomers(selectedRowKeys);
      message.success(`已删除 ${selectedRowKeys.length} 条`);
      setSelectedRowKeys([]);
      fetch();
    } catch { message.error("批量删除失败"); }
  };

  const handleBatchTag = async () => {
    if (batchTagIds.length === 0) return;
    try {
      await batchTagCustomers(selectedRowKeys, batchTagIds);
      message.success(`已为 ${selectedRowKeys.length} 个客户添加标签`);
      setSelectedRowKeys([]);
      setTagModalOpen(false);
      setBatchTagIds([]);
      fetch();
    } catch { message.error("批量打标签失败"); }
  };

  const columns = [
    { title: "客户编码", dataIndex: "code", width: 120 },
    { title: "客户名称", dataIndex: "name", width: 200, render: (text: string, r: Customer) => (
      <a onClick={() => navigate(`/customers/${r.id}`)}>{text}</a>
    )},
    { title: "行业", dataIndex: "industry", width: 100 },
    { title: "等级", dataIndex: "level", width: 80, render: (v: string) => <Tag color={v === "A" ? "red" : v === "B" ? "orange" : "default"}>{v}</Tag> },
    { title: "区域", dataIndex: "region", width: 100 },
    { title: "标签", dataIndex: "tags", width: 160, render: (tags: TagType[]) => (
      tags?.map((t) => <Tag key={t.id} color={t.color || "blue"}>{t.name}</Tag>)
    )},
    { title: "联系人", dataIndex: "contact_person", width: 100 },
    { title: "来源", dataIndex: "source", width: 80 },
    {
      title: "操作", key: "actions", width: 150, render: (_: unknown, r: Customer) => (
        <Space>
          <Button size="small" onClick={() => navigate(`/customers/${r.id}`)}>详情</Button>
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
              onPressEnter={() => { setPage(1); fetch(1, q); }}
              style={{ width: 240 }}
            />
          </Col>
          <Col><Select allowClear placeholder="行业" style={{ width: 120 }} value={industry} onChange={(v) => { setIndustry(v); setPage(1); }} options={INDUSTRIES.map((v) => ({ value: v, label: v }))} /></Col>
          <Col><Select allowClear placeholder="等级" style={{ width: 80 }} value={level} onChange={(v) => { setLevel(v); setPage(1); }} options={LEVELS.map((v) => ({ value: v, label: v }))} /></Col>
          <Col><Select allowClear placeholder="区域" style={{ width: 100 }} value={region} onChange={(v) => { setRegion(v); setPage(1); }} options={REGIONS.map((v) => ({ value: v, label: v }))} /></Col>
          <Col><Select allowClear placeholder="来源" style={{ width: 100 }} value={source} onChange={(v) => { setSource(v); setPage(1); }} options={SOURCES.map((v) => ({ value: v, label: v }))} /></Col>
          <Col><Select allowClear placeholder="信用等级" style={{ width: 100 }} value={creditLevel} onChange={(v) => { setCreditLevel(v); setPage(1); }} options={LEVELS.map((v) => ({ value: v, label: v }))} /></Col>
          <Col>
            <Button onClick={() => { setPage(1); fetch(1, q); }}>搜索</Button>
          </Col>
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
              <Button icon={<DownloadOutlined />} onClick={handleExport}>导出</Button>
              <Button type="primary" icon={<PlusOutlined />} onClick={() => navigate("/customers/new")}>新建客户</Button>
            </Space>
          </Col>
        </Row>
      </Card>

      <Table
        rowKey="id"
        columns={columns}
        dataSource={data}
        loading={loading}
        rowSelection={{
          selectedRowKeys,
          onChange: (keys) => setSelectedRowKeys(keys as number[]),
        }}
        pagination={{ current: page, total, pageSize: 20, onChange: setPage, showTotal: (t) => `共 ${t} 条`, showSizeChanger: false }}
      />

      <Modal title="选择标签" open={tagModalOpen} onCancel={() => setTagModalOpen(false)} onOk={handleBatchTag}>
        <Select
          mode="multiple"
          style={{ width: "100%" }}
          placeholder="选择要添加的标签"
          value={batchTagIds}
          onChange={(v) => setBatchTagIds(v)}
          options={tags.map((t) => ({ value: t.id, label: t.name }))}
        />
      </Modal>
    </div>
  );
}
