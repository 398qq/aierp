import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Table, Button, Space, Tag, Select, message, Popconfirm, Switch } from "antd";
import { PlusOutlined, DeleteOutlined } from "@ant-design/icons";
import { getDeliveryNotes, batchDeleteDeliveryNotes, deleteDeliveryNote } from "../../api";
import AIInlineBadge from "../../components/sales/AIInlineBadge";
import type { DeliveryNote } from "../../types";

const STATUS: Record<string, { color: string; label: string }> = {
  pending: { color: "default", label: "待发货" }, shipped: { color: "blue", label: "已发货" },
  delivered: { color: "green", label: "已签收" }, returned: { color: "red", label: "已退回" },
};

export default function DeliveryNoteList() {
  const [data, setData] = useState<DeliveryNote[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState<string | undefined>();
  const [includeAi, setIncludeAi] = useState(false);
  const [aiMap, setAiMap] = useState<Record<number, { completion_risk?: string; flag?: string }>>({});
  const [selected, setSelected] = useState<number[]>([]);
  const navigate = useNavigate();

  const load = async () => {
    setLoading(true);
    try {
      const params: Record<string, unknown> = { page, page_size: 20 };
      if (status) params.status = status;
      if (includeAi) params.include_ai = true;
      const resp = await getDeliveryNotes(params);
      setData(resp.data.data.list || []);
      setTotal(resp.data.data.total || 0);
      if (includeAi) setAiMap((resp.data.data as unknown as Record<string, unknown>).ai as Record<string, { completion_risk?: string; flag?: string }> || {});
      else setAiMap({});
    } catch { message.error("加载失败"); }
    finally { setLoading(false); }
  };

  useEffect(() => { load(); }, [page, status, includeAi]);

  const handleBatchDelete = async () => {
    try { await batchDeleteDeliveryNotes(selected); message.success("已批量删除"); setSelected([]); load(); } catch { message.error("删除失败"); }
  };

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => navigate("/sales/delivery-notes/new")}>新增发货单</Button>
        {selected.length > 0 && (
          <Popconfirm title="确定批量删除?" onConfirm={handleBatchDelete}><Button danger icon={<DeleteOutlined />}>删除({selected.length})</Button></Popconfirm>
        )}
        <Select placeholder="状态筛选" allowClear style={{ width: 120 }} value={status} onChange={setStatus} options={[
          { value: "pending", label: "待发货" }, { value: "shipped", label: "已发货" }, { value: "delivered", label: "已签收" },
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
          { title: "发货单号", dataIndex: "delivery_no", width: 140, render: (v: string, r: DeliveryNote) => <a onClick={() => navigate(`/sales/delivery-notes/${r.id}`)}>{v || `#${r.id}`}</a> },
          { title: "订单ID", dataIndex: "sales_order_id", width: 80 },
          { title: "状态", dataIndex: "status", width: 80, render: (v: string) => <Tag color={STATUS[v]?.color}>{STATUS[v]?.label || v}</Tag> },
          { title: "发货日期", dataIndex: "delivery_date", width: 110, render: (v: string) => v?.slice(0, 10) || "-" },
          { title: "签收日期", dataIndex: "received_date", width: 110, render: (v: string) => v?.slice(0, 10) || "-" },
          {
            title: "AI", width: 90,
            render: (_: unknown, r: DeliveryNote) => <AIInlineBadge riskLevel={aiMap[r.id]?.completion_risk} flag={aiMap[r.id]?.flag} />,
          },
          {
            title: "操作", width: 120,
            render: (_: unknown, r: DeliveryNote) => (
              <Space size="small">
                <Button size="small" onClick={() => navigate(`/sales/delivery-notes/${r.id}`)}>详情</Button>
                <Popconfirm title="确定删除?" onConfirm={async () => {
                  try { await deleteDeliveryNote(r.id); message.success("已删除"); load(); } catch { message.error("删除失败"); }
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
