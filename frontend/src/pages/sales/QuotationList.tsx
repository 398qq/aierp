import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Table, Button, Space, Tag, Select, message, Popconfirm, Switch } from "antd";
import { PlusOutlined, DeleteOutlined } from "@ant-design/icons";
import { getQuotations, batchDeleteQuotations, deleteQuotation, convertQuotationToOrder, downloadQuotationPDF } from "../../api";
import AIInlineBadge from "../../components/sales/AIInlineBadge";
import type { Quotation } from "../../types";

const STATUS: Record<string, { color: string; label: string }> = {
  draft: { color: "default", label: "草稿" }, sent: { color: "blue", label: "已发送" },
  won: { color: "green", label: "成交" }, lost: { color: "red", label: "丢失" },
};

export default function QuotationList() {
  const [data, setData] = useState<Quotation[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState<string | undefined>();
  const [includeAi, setIncludeAi] = useState(false);
  const [aiMap, setAiMap] = useState<Record<number, { pricing_health?: string; flag?: string }>>({});
  const [selected, setSelected] = useState<number[]>([]);
  const navigate = useNavigate();

  const load = async () => {
    setLoading(true);
    try {
      const params: Record<string, unknown> = { page, page_size: 20 };
      if (status) params.status = status;
      if (includeAi) params.include_ai = true;
      const resp = await getQuotations(params);
      setData(resp.data.data.list || []);
      setTotal(resp.data.data.total || 0);
      if (includeAi) setAiMap((resp.data.data as unknown as Record<string, unknown>).ai as Record<string, { pricing_health?: string; flag?: string }> || {});
      else setAiMap({});
    } catch { message.error("加载失败"); }
    finally { setLoading(false); }
  };

  useEffect(() => { load(); }, [page, status, includeAi]);

  const handleBatchDelete = async () => {
    try { await batchDeleteQuotations(selected); message.success("已批量删除"); setSelected([]); load(); } catch { message.error("删除失败"); }
  };

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => navigate("/sales/quotations/new")}>新增报价</Button>
        {selected.length > 0 && (
          <Popconfirm title="确定批量删除?" onConfirm={handleBatchDelete}><Button danger icon={<DeleteOutlined />}>删除({selected.length})</Button></Popconfirm>
        )}
        <Select placeholder="状态筛选" allowClear style={{ width: 120 }} value={status} onChange={setStatus} options={[
          { value: "draft", label: "草稿" }, { value: "sent", label: "已发送" }, { value: "won", label: "成交" },
        ]} />
        <Space>
          <Switch checked={includeAi} onChange={setIncludeAi} size="small" />
          <span style={{ fontSize: 13 }}>AI</span>
        </Space>
      </Space>

      <Table
        rowKey="id"
        loading={loading}
        dataSource={data}
        rowSelection={{ selectedRowKeys: selected, onChange: (keys) => setSelected(keys as number[]) }}
        columns={[
          { title: "报价单号", dataIndex: "quotation_no", width: 140, render: (v: string, r: Quotation) => <a onClick={() => navigate(`/sales/quotations/${r.id}`)}>{v || `#${r.id}`}</a> },
          { title: "标题", dataIndex: "title", ellipsis: true },
          { title: "金额", dataIndex: "total_amount", width: 120, render: (v: number) => `¥${v.toLocaleString()}` },
          { title: "状态", dataIndex: "status", width: 80, render: (v: string) => <Tag color={STATUS[v]?.color}>{STATUS[v]?.label || v}</Tag> },
          { title: "有效期", dataIndex: "valid_until", width: 110, render: (v: string) => v?.slice(0, 10) || "-" },
          {
            title: "AI", width: 90,
            render: (_: unknown, r: Quotation) => <AIInlineBadge riskLevel={aiMap[r.id]?.pricing_health === "poor" ? "high" : aiMap[r.id]?.pricing_health === "fair" ? "medium" : "low"} flag={aiMap[r.id]?.flag} />,
          },
          {
            title: "操作", width: 220,
            render: (_: unknown, r: Quotation) => (
              <Space size="small">
                <Button size="small" onClick={() => navigate(`/sales/quotations/${r.id}`)}>详情</Button>
                <Button size="small" onClick={() => { downloadQuotationPDF(r.id, `quotation_${r.quotation_no || r.id}.pdf`).catch(() => message.error("下载失败")); }}>PDF</Button>
                {r.status !== "won" && (
                  <Popconfirm title="转为销售订单?" onConfirm={async () => {
                    try { await convertQuotationToOrder(r.id); message.success("已转为订单"); load(); } catch { message.error("转换失败"); }
                  }}><Button size="small" type="primary">转订单</Button></Popconfirm>
                )}
                <Popconfirm title="确定删除?" onConfirm={async () => {
                  try { await deleteQuotation(r.id); message.success("已删除"); load(); } catch { message.error("删除失败"); }
                }}><Button size="small" danger>删除</Button></Popconfirm>
              </Space>
            ),
          },
        ]}
        pagination={{ current: page, total, pageSize: 20, onChange: setPage, showTotal: (t) => `共 ${t} 条` }}
      />
    </div>
  );
}
