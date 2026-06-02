import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Table, Button, Space, Tag, Select, message, Popconfirm, Row, Col, Card, Statistic } from "antd";
import { PlusOutlined } from "@ant-design/icons";
import { getPayments, deletePayment, getPaymentStats } from "../../api";
import type { PaymentRecord } from "../../types";
import { CustomerLink, CustomerSelect, SalesModuleShell } from "./salesUi";

const STATUS: Record<string, { color: string; label: string }> = {
  pending: { color: "orange", label: "待收款" }, completed: { color: "green", label: "已收款" },
  overdue: { color: "red", label: "逾期" }, cancelled: { color: "default", label: "已取消" },
};

export default function PaymentList() {
  const [data, setData] = useState<PaymentRecord[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState<string | undefined>();
  const [customerId, setCustomerId] = useState<number | undefined>();
  const [stats, setStats] = useState<{ total_received: number; total_pending: number; total_overdue: number }>({ total_received: 0, total_pending: 0, total_overdue: 0 });
  const navigate = useNavigate();

  const load = async () => {
    setLoading(true);
    try {
      const params: Record<string, unknown> = { page, page_size: 20 };
      if (status) params.status = status;
      if (customerId) params.customer_id = customerId;
      const [resp, s] = await Promise.all([getPayments(params), getPaymentStats()]);
      setData(resp.data.data.list || []);
      setTotal(resp.data.data.total || 0);
      setStats(s.data.data);
    } catch { message.error("加载失败"); }
    finally { setLoading(false); }
  };

  useEffect(() => { load(); }, [page, status, customerId]);

  return (
    <SalesModuleShell
      title="回款管理"
      subtitle="按客户和订单跟踪待收、已收、逾期回款"
      activeKey="payments"
    >
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}><Card size="small"><Statistic title="已收款" value={stats.total_received} prefix="¥" valueStyle={{ color: "#52c41a" }} /></Card></Col>
        <Col span={6}><Card size="small"><Statistic title="待收款" value={stats.total_pending} prefix="¥" valueStyle={{ color: "#faad14" }} /></Card></Col>
        <Col span={6}><Card size="small"><Statistic title="逾期" value={stats.total_overdue} prefix="¥" valueStyle={{ color: "#ff4d4f" }} /></Card></Col>
      </Row>

      <Space style={{ marginBottom: 16 }}>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => navigate("/sales/payments/new")}>新增回款</Button>
        <Select placeholder="状态筛选" allowClear style={{ width: 120 }} value={status} onChange={setStatus} options={[
          { value: "pending", label: "待收款" }, { value: "completed", label: "已收款" },
        ]} />
        <div style={{ width: 280 }}>
          <CustomerSelect value={customerId} onChange={(next) => { setCustomerId(next); setPage(1); }} />
        </div>
      </Space>

      <Table
        rowKey="id" loading={loading} dataSource={data}
        columns={[
          { title: "ID", dataIndex: "id", width: 60 },
          {
            title: "关联订单", dataIndex: "sales_order_id", width: 100,
            render: (value: number) => (
              <a onClick={() => navigate(`/sales/orders/${value}`)}>#{value}</a>
            ),
          },
          {
            title: "发货单", dataIndex: "delivery_note_id", width: 100,
            render: (value: number | null) => {
              if (!value) return <span style={{ color: "#999" }}>-</span>;
              return (
                <a onClick={() => navigate(`/sales/delivery-notes/${value}`)}>#{value}</a>
              );
            },
          },
          { title: "客户", dataIndex: "customer_id", width: 180, render: (value: number) => <CustomerLink id={value} /> },
          { title: "金额", dataIndex: "amount", width: 120, render: (v: number) => `¥${v.toLocaleString()}` },
          { title: "方式", dataIndex: "payment_method", width: 80 },
          { title: "付款日期", dataIndex: "payment_date", width: 110, render: (v: string) => v?.slice(0, 10) || "-" },
          { title: "状态", dataIndex: "status", width: 80, render: (v: string) => <Tag color={STATUS[v]?.color}>{STATUS[v]?.label || v}</Tag> },
          {
            title: "操作", width: 120,
            render: (_: unknown, r: PaymentRecord) => (
              <Space size="small">
                <Button size="small" onClick={() => navigate(`/sales/payments/${r.id}/edit`)}>编辑</Button>
                <Popconfirm title="确定删除?" onConfirm={async () => {
                  try { await deletePayment(r.id); message.success("已删除"); load(); } catch { message.error("删除失败"); }
                }}><Button size="small" danger>删除</Button></Popconfirm>
              </Space>
            ),
          },
        ]}
        pagination={{ current: page, total, pageSize: 20, onChange: setPage, showTotal: (t) => `共 ${t} 条` }}
      />
    </SalesModuleShell>
  );
}
